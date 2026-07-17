"""Focused safety contracts for Asset Vault archive inspection and restore."""

from __future__ import annotations

import importlib
from pathlib import Path
import sqlite3
import sys

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_auth_throttle",
    "copyfast_bridge", "copyfast_registry", "copyfast_api", "copyfast_pages",
    "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_support",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "asset-vault-lifecycle.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "asset-vault-lifecycle-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_SUPPORT_DESK_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "6")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "20")
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
            "display_name": "Asset Lifecycle Owner",
        },
    )
    assert registered.status_code == 200, registered.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200, login.text
    return login.json()["data"]["csrf_token"]


def upload_text(client: TestClient, csrf: str, *, key: str, content: bytes = b"safe lifecycle content") -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Tệp kiem tra vong doi"},
        files={"file": ("lifecycle.txt", content, "text/plain")},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["asset"]


def archive(
    client: TestClient,
    csrf: str,
    asset_id: str,
    *,
    key: str,
    revision: int | None = None,
) -> dict:
    if revision is None:
        current = lifecycle(client, asset_id)
        assert current["ok"] is True
        revision = current["data"]["lifecycle"]["lifecycle_revision"]
    response = client.post(
        f"/api/v1/asset-vault/{asset_id}/archive",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        json={"expected_revision": revision},
    )
    assert response.status_code == 200, response.text
    return response.json()


def lifecycle(client: TestClient, asset_id: str) -> dict:
    response = client.get(f"/api/v1/asset-vault/{asset_id}/lifecycle")
    assert response.status_code == 200, response.text
    return response.json()


def restore(client: TestClient, csrf: str, asset_id: str, *, revision: int, key: str):
    return client.post(
        f"/api/v1/asset-vault/{asset_id}/restore",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": revision, "idempotency_key": key},
    )


def test_lifecycle_revision_is_additive_for_an_existing_asset_vault_database(tmp_path, monkeypatch):
    """The migration must not require dropping or recreating retained blobs."""
    database_path = tmp_path / "asset-vault-lifecycle.db"
    with sqlite3.connect(database_path) as conn:
        conn.execute(
            """CREATE TABLE web_asset_files (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                project_id TEXT,
                display_name TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                extension TEXT NOT NULL,
                content_type TEXT NOT NULL,
                byte_size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                storage_key TEXT NOT NULL UNIQUE,
                state TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                archived_at TEXT
            )"""
        )

    with make_client(tmp_path, monkeypatch):
        with sqlite3.connect(database_path) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(web_asset_files)").fetchall()}
            indexes = {row[1] for row in conn.execute("PRAGMA index_list(web_asset_files)").fetchall()}
    assert "lifecycle_revision" in columns
    assert "idx_web_asset_files_owner_state_lifecycle" in indexes


def test_lifecycle_is_owner_scoped_redacted_and_archive_advances_revision(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = register_and_login(owner, "lifecycle-owner@example.com")
        asset = upload_text(owner, csrf, key="asset-lifecycle-upload-0001")

        with sqlite3.connect(tmp_path / "asset-vault-lifecycle.db") as conn:
            storage_key, digest = conn.execute(
                "SELECT storage_key, sha256 FROM web_asset_files WHERE id=?", (asset["id"],)
            ).fetchone()

        active = lifecycle(owner, asset["id"])
        active_lifecycle = active["data"]["lifecycle"]
        assert active_lifecycle["state"] == "active"
        assert active_lifecycle["lifecycle_revision"] == 1
        assert active_lifecycle["restore_available"] is False
        assert active_lifecycle["reference_summary"] == {
            "total_count": 0,
            "hard_blocker_count": 0,
            "references": [],
        }
        for private_value in (asset["id"], storage_key, digest, str(tmp_path / "private-assets")):
            assert private_value not in str(active)
        assert {"storage_key", "sha256", "account_id", "project_id"}.isdisjoint(active_lifecycle)

        archive(owner, csrf, asset["id"], key="asset-lifecycle-archive-0001")
        archived = lifecycle(owner, asset["id"])
        archived_lifecycle = archived["data"]["lifecycle"]
        assert archived_lifecycle["state"] == "archived"
        assert archived_lifecycle["lifecycle_revision"] == 2
        assert archived_lifecycle["restore_available"] is True

        with make_client(tmp_path, monkeypatch) as foreign:
            register_and_login(foreign, "lifecycle-foreign@example.com")
            hidden = foreign.get(f"/api/v1/asset-vault/{asset['id']}/lifecycle")
            assert hidden.status_code == 200
            assert hidden.json()["error_code"] == "WEB_ASSET_NOT_FOUND"
            assert storage_key not in hidden.text
            assert digest not in hidden.text


def test_archive_requires_current_revision_and_binds_it_to_idempotency(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "archive-concurrency-owner@example.com")
        asset = upload_text(client, csrf, key="asset-archive-concurrency-upload-0001")

        missing_revision = client.post(
            f"/api/v1/asset-vault/{asset['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "asset-archive-missing-revision-0001"},
        )
        assert missing_revision.status_code == 422

        stale = archive(
            client,
            csrf,
            asset["id"],
            key="asset-archive-revision-bound-0001",
            revision=2,
        )
        assert stale["error_code"] == "WEB_ASSET_LIFECYCLE_CONFLICT"
        active_after_stale = lifecycle(client, asset["id"])["data"]["lifecycle"]
        assert active_after_stale["state"] == "active"
        assert active_after_stale["lifecycle_revision"] == 1
        assert active_after_stale["restore_available"] is False

        # A replay key is tied to the lifecycle version too: it cannot turn a
        # prior rejected stale request into a valid archive after a refresh.
        key_reused_with_current_revision = client.post(
            f"/api/v1/asset-vault/{asset['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "asset-archive-revision-bound-0001"},
            json={"expected_revision": 1},
        )
        assert key_reused_with_current_revision.status_code == 409
        assert lifecycle(client, asset["id"])["data"]["lifecycle"]["state"] == "active"

        archived = archive(
            client,
            csrf,
            asset["id"],
            key="asset-archive-current-revision-0001",
            revision=1,
        )
        assert archived["ok"] is True
        assert lifecycle(client, asset["id"])["data"]["lifecycle"]["lifecycle_revision"] == 2


def test_document_and_image_source_guards_advance_asset_lifecycle_revision(tmp_path, monkeypatch):
    """Every native source-integrity guard must invalidate stale Vault actions."""
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "source-guard-lifecycle-owner@example.com")
        document_asset = upload_text(client, csrf, key="asset-source-guard-document-upload-0001")
        image_asset = upload_text(client, csrf, key="asset-source-guard-image-upload-0001")
        with sqlite3.connect(tmp_path / "asset-vault-lifecycle.db") as conn:
            account_id = conn.execute(
                "SELECT id FROM web_accounts WHERE email=?",
                ("source-guard-lifecycle-owner@example.com",),
            ).fetchone()[0]

        document_operations = importlib.import_module("copyfast_document_operations")
        image_operations = importlib.import_module("copyfast_image_operations")
        document_operations._mark_source_unavailable(document_asset["id"], str(account_id))
        image_operations._mark_source_unavailable(image_asset["id"], str(account_id))

        for asset in (document_asset, image_asset):
            guarded = lifecycle(client, asset["id"])["data"]["lifecycle"]
            assert guarded["state"] == "unavailable"
            assert guarded["lifecycle_revision"] == 2

        # Both writers are state-scoped, so an already guarded asset cannot
        # keep moving the revision or make a client perpetually stale.
        document_operations._mark_source_unavailable(document_asset["id"], str(account_id))
        image_operations._mark_source_unavailable(image_asset["id"], str(account_id))
        assert lifecycle(client, document_asset["id"])["data"]["lifecycle"]["lifecycle_revision"] == 2
        assert lifecycle(client, image_asset["id"])["data"]["lifecycle"]["lifecycle_revision"] == 2


def test_restore_requires_csrf_revision_and_idempotency_then_reactivates_private_download(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "restore-owner@example.com")
        asset = upload_text(client, csrf, key="asset-restore-upload-0001")
        archive(client, csrf, asset["id"], key="asset-restore-archive-0001")
        archived_revision = lifecycle(client, asset["id"])["data"]["lifecycle"]["lifecycle_revision"]
        assert archived_revision == 2

        csrf_denied = client.post(
            f"/api/v1/asset-vault/{asset['id']}/restore",
            json={"expected_revision": archived_revision, "idempotency_key": "asset-restore-no-csrf-0001"},
        )
        assert csrf_denied.status_code == 403

        stale = restore(
            client,
            csrf,
            asset["id"],
            revision=archived_revision - 1,
            key="asset-restore-stale-0001",
        )
        assert stale.status_code == 200
        assert stale.json()["error_code"] == "WEB_ASSET_LIFECYCLE_CONFLICT"

        restored = restore(
            client,
            csrf,
            asset["id"],
            revision=archived_revision,
            key="asset-restore-valid-0001",
        )
        assert restored.status_code == 200, restored.text
        restored_body = restored.json()
        assert restored_body["ok"] is True
        assert restored_body["data"]["asset"]["state"] == "active"
        assert restored_body["data"]["lifecycle"]["lifecycle_revision"] == archived_revision + 1
        assert restored_body["data"]["lifecycle"]["archived_at"] is None

        replay = restore(
            client,
            csrf,
            asset["id"],
            revision=archived_revision,
            key="asset-restore-valid-0001",
        )
        assert replay.status_code == 200
        assert replay.json() == restored_body
        assert client.get(f"/api/v1/asset-vault/{asset['id']}/download").content == b"safe lifecycle content"

        with sqlite3.connect(tmp_path / "asset-vault-lifecycle.db") as conn:
            restore_audits = conn.execute(
                "SELECT target, detail FROM web_audit_events WHERE action='web.asset_vault.restore'"
            ).fetchall()
        assert restore_audits
        assert all(target == "" and detail == "" for target, detail in restore_audits)


def test_restore_marks_missing_or_corrupt_archived_blobs_unavailable_without_private_details(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "integrity-owner@example.com")
        corrupt_asset = upload_text(client, csrf, key="asset-integrity-corrupt-upload-0001")
        missing_asset = upload_text(client, csrf, key="asset-integrity-missing-upload-0001")
        archive(client, csrf, corrupt_asset["id"], key="asset-integrity-corrupt-archive-0001")
        archive(client, csrf, missing_asset["id"], key="asset-integrity-missing-archive-0001")

        with sqlite3.connect(tmp_path / "asset-vault-lifecycle.db") as conn:
            rows = dict(conn.execute(
                "SELECT id, storage_key FROM web_asset_files WHERE id IN (?, ?)",
                (corrupt_asset["id"], missing_asset["id"]),
            ).fetchall())
        corrupt_path = Path(tmp_path / "private-assets") / rows[corrupt_asset["id"]]
        missing_path = Path(tmp_path / "private-assets") / rows[missing_asset["id"]]
        corrupt_path.write_bytes(b"tampered archived bytes")
        missing_path.unlink()

        for asset, key in (
            (corrupt_asset, "asset-integrity-corrupt-restore-0001"),
            (missing_asset, "asset-integrity-missing-restore-0001"),
        ):
            revision = lifecycle(client, asset["id"])["data"]["lifecycle"]["lifecycle_revision"]
            guarded = restore(client, csrf, asset["id"], revision=revision, key=key)
            assert guarded.status_code == 200
            assert guarded.json()["error_code"] == "WEB_ASSET_UNAVAILABLE"
            current = guarded.json()["data"]["lifecycle"]
            assert current["state"] == "unavailable"
            assert current["lifecycle_revision"] == revision + 1
            assert current["restore_available"] is False
            assert rows[asset["id"]] not in guarded.text
            assert client.get(f"/api/v1/asset-vault/{asset['id']}/download").json()["error_code"] == "WEB_ASSET_NOT_FOUND"


def test_support_evidence_is_retained_across_restore_and_corruption_stays_fail_closed(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "evidence-lifecycle-owner@example.com")
        asset = upload_text(
            client,
            csrf,
            key="asset-evidence-lifecycle-upload-0001",
            content=b"browser trace without private credentials",
        )
        case_response = client.post(
            "/api/v1/support/cases",
            headers={"X-CSRF-Token": csrf},
            json={
                "category": "image_error",
                "priority": "high",
                "subject": "Can kiem tra tai nguyen Web",
                "detail": "Tai nguyen khong hien thi trong khu vuc lam viec cua toi.",
                "idempotency_key": "asset-evidence-lifecycle-case-0001",
            },
        )
        assert case_response.status_code == 200, case_response.text
        case = case_response.json()["data"]["case"]
        attached = client.post(
            f"/api/v1/support/cases/{case['id']}/attachments",
            headers={"X-CSRF-Token": csrf},
            json={
                "asset_id": asset["id"],
                "expected_revision": 1,
                "idempotency_key": "asset-evidence-lifecycle-attach-0001",
                "customer_redaction_confirmed": True,
            },
        )
        assert attached.status_code == 200, attached.text
        attachment = attached.json()["data"]["attachment"]

        archive(client, csrf, asset["id"], key="asset-evidence-lifecycle-archive-0001")
        archived_lifecycle_response = lifecycle(client, asset["id"])
        archived_lifecycle = archived_lifecycle_response["data"]["lifecycle"]
        assert archived_lifecycle["lifecycle_revision"] == 2
        assert archived_lifecycle["reference_summary"] == {
            "total_count": 1,
            "hard_blocker_count": 1,
            "references": [{
                "reason": "support_evidence_retention",
                "count": 1,
                "hard_blocker": True,
            }],
        }
        for private_value in (asset["id"], case["id"]):
            assert private_value not in str(archived_lifecycle_response)

        evidence_url = f"/api/v1/support/cases/{case['id']}/attachments/{attachment['id']}/download"
        assert client.get(evidence_url).content == b"browser trace without private credentials"
        restored = restore(
            client,
            csrf,
            asset["id"],
            revision=archived_lifecycle["lifecycle_revision"],
            key="asset-evidence-lifecycle-restore-0001",
        )
        assert restored.json()["ok"] is True
        assert client.get(evidence_url).content == b"browser trace without private credentials"

        archive(client, csrf, asset["id"], key="asset-evidence-lifecycle-archive-0002")
        with sqlite3.connect(tmp_path / "asset-vault-lifecycle.db") as conn:
            storage_key = conn.execute(
                "SELECT storage_key FROM web_asset_files WHERE id=?", (asset["id"],)
            ).fetchone()[0]
        (Path(tmp_path / "private-assets") / storage_key).write_bytes(b"corrupted evidence")
        unavailable_evidence = client.get(evidence_url)
        assert unavailable_evidence.status_code == 200
        assert unavailable_evidence.json()["error_code"] == "WEB_SUPPORT_ATTACHMENT_UNAVAILABLE"
        unavailable_lifecycle = lifecycle(client, asset["id"])["data"]["lifecycle"]
        assert unavailable_lifecycle["state"] == "unavailable"
        assert storage_key not in str(unavailable_lifecycle)
