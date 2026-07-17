"""Focused contracts for private Support Desk evidence links.

The feature deliberately reuses the owner-scoped Asset Vault rather than
introducing a second upload surface in Support Desk.  These tests exercise
the real signed-session/CSRF/download boundary without Bot, provider, wallet
or payment state.
"""

from __future__ import annotations

import importlib
import sqlite3
import sys
import uuid

from fastapi.testclient import TestClient


MODULES = [
    "app", "copyfast_db", "copyfast_auth", "copyfast_auth_throttle",
    "copyfast_bridge", "copyfast_registry", "copyfast_api", "copyfast_pages",
    "copyfast_projects", "copyfast_assets", "copyfast_project_packages",
    "copyfast_document_operations", "copyfast_image_runtime",
    "copyfast_image_operations", "copyfast_support",
]


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "support-evidence.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "support-evidence-session-secret")
    monkeypatch.setenv("WEBAPP_SUPPORT_DESK_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
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


def register_and_login(client: TestClient, email: str, *, display_name: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": display_name,
        },
    )
    assert registered.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200
    return login.json()["data"]["csrf_token"]


def login(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["csrf_token"]


def upload_text(client: TestClient, csrf: str, *, key: str, content: bytes, name: str = "evidence.txt") -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "Nhật ký lỗi đã che dữ liệu"},
        files={"file": (name, content, "text/plain")},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["asset"]


def create_case(client: TestClient, csrf: str, *, key: str, category: str = "image_error") -> dict:
    response = client.post(
        "/api/v1/support/cases",
        headers={"X-CSRF-Token": csrf},
        json={
            "category": category,
            "priority": "high",
            "subject": "Cần kiểm tra lỗi hiển thị Web",
            "detail": "Khu vực làm việc không tải được nội dung đã lưu của tôi.",
            "idempotency_key": key,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["case"]


def attach(client: TestClient, csrf: str, case_id: str, asset_id: str, *, revision: int, key: str, confirmed: bool = True):
    return client.post(
        f"/api/v1/support/cases/{case_id}/attachments",
        headers={"X-CSRF-Token": csrf},
        json={
            "asset_id": asset_id,
            "expected_revision": revision,
            "idempotency_key": key,
            "customer_redaction_confirmed": confirmed,
        },
    )


def test_support_evidence_is_private_idempotent_and_survives_asset_archive(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = register_and_login(owner, "evidence-owner@example.com", display_name="Evidence Owner")
        asset = upload_text(owner, csrf, key="support-evidence-asset-0001", content=b"browser console trace without credentials")
        case = create_case(owner, csrf, key="support-evidence-case-0001")

        denied = owner.post(
            f"/api/v1/support/cases/{case['id']}/attachments",
            json={
                "asset_id": asset["id"], "expected_revision": 1,
                "idempotency_key": "support-evidence-no-csrf-0001",
                "customer_redaction_confirmed": True,
            },
        )
        assert denied.status_code == 403

        missing_attestation = attach(
            owner, csrf, case["id"], asset["id"], revision=1,
            key="support-evidence-attestation-0001", confirmed=False,
        )
        assert missing_attestation.status_code == 422

        with sqlite3.connect(tmp_path / "support-evidence.db") as conn:
            waiting_before = conn.execute(
                "SELECT customer_waiting_since FROM web_support_cases WHERE id=?", (case["id"],)
            ).fetchone()[0]

        linked = attach(
            owner, csrf, case["id"], asset["id"], revision=1,
            key="support-evidence-link-0001",
        )
        assert linked.status_code == 200, linked.text
        linked_body = linked.json()
        assert linked_body["ok"] is True
        assert linked_body["data"]["case"]["revision"] == 2
        attachment = linked_body["data"]["attachment"]
        assert attachment["content_type"] == "text/plain"
        assert attachment["byte_size"] == len(b"browser console trace without credentials")
        assert asset["id"] not in str(attachment)
        assert "storage_key" not in linked.text
        assert "sha256" not in linked.text

        replay = attach(
            owner, csrf, case["id"], asset["id"], revision=1,
            key="support-evidence-link-0001",
        )
        assert replay.status_code == 200
        assert replay.json() == linked_body

        detail = owner.get(f"/api/v1/support/cases/{case['id']}")
        assert detail.status_code == 200
        assert detail.json()["data"]["attachments"] == [attachment]
        assert "customer_attachment_added" in {item["action"] for item in detail.json()["data"]["events"]}
        with sqlite3.connect(tmp_path / "support-evidence.db") as conn:
            waiting_after = conn.execute(
                "SELECT customer_waiting_since FROM web_support_cases WHERE id=?", (case["id"],)
            ).fetchone()[0]
        assert waiting_after == waiting_before

        download = owner.get(
            f"/api/v1/support/cases/{case['id']}/attachments/{attachment['id']}/download"
        )
        assert download.status_code == 200
        assert download.content == b"browser console trace without credentials"
        assert download.headers["cache-control"] == "no-store, private"
        assert download.headers["x-content-type-options"] == "nosniff"
        assert download.headers["referrer-policy"] == "no-referrer"
        assert download.headers["content-security-policy"] == "sandbox"

        archived = owner.post(
            f"/api/v1/asset-vault/{asset['id']}/archive",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "support-evidence-archive-0001"},
            json={"expected_revision": 1},
        )
        assert archived.status_code == 200
        assert archived.json()["data"]["asset"]["state"] == "archived"
        still_private = owner.get(
            f"/api/v1/support/cases/{case['id']}/attachments/{attachment['id']}/download"
        )
        assert still_private.status_code == 200
        assert still_private.content == b"browser console trace without credentials"

    with make_client(tmp_path, monkeypatch) as stranger:
        stranger_csrf = register_and_login(stranger, "evidence-stranger@example.com", display_name="Evidence Stranger")
        hidden = stranger.get(
            f"/api/v1/support/cases/{case['id']}/attachments/{attachment['id']}/download"
        )
        assert hidden.status_code == 200
        assert hidden.json()["error_code"] == "WEB_SUPPORT_ATTACHMENT_NOT_FOUND"
        assert attachment["display_name"] not in hidden.text

        with sqlite3.connect(tmp_path / "support-evidence.db") as conn:
            conn.execute(
                "UPDATE web_accounts SET role_cache='support_operator' WHERE email='evidence-stranger@example.com'"
            )
            conn.commit()
        staff_download = stranger.get(
            f"/api/v1/support/admin/cases/{case['id']}/attachments/{attachment['id']}/download"
        )
        assert staff_download.status_code == 200
        assert staff_download.content == b"browser console trace without credentials"
        assert stranger_csrf


def test_support_evidence_rejects_foreign_stale_sensitive_and_payment_paths(tmp_path, monkeypatch):
    with make_client(tmp_path, monkeypatch) as owner:
        csrf = register_and_login(owner, "evidence-guard-owner@example.com", display_name="Evidence Guard Owner")
        safe_asset = upload_text(owner, csrf, key="support-evidence-guard-safe-0001", content=b"safe error summary")
        unsafe_asset = upload_text(
            owner, csrf, key="support-evidence-guard-sensitive-0001",
            content=b"token: abcdefghijklmnopqrstuvwxyz0123456789",
            name="unsafe-log.txt",
        )
        case = create_case(owner, csrf, key="support-evidence-guard-case-0001")

        stale = attach(
            owner, csrf, case["id"], safe_asset["id"], revision=2,
            key="support-evidence-guard-stale-0001",
        )
        assert stale.status_code == 200
        assert stale.json()["error_code"] == "WEB_SUPPORT_CASE_CONFLICT"

        sensitive = attach(
            owner, csrf, case["id"], unsafe_asset["id"], revision=1,
            key="support-evidence-guard-sensitive-link-0001",
        )
        assert sensitive.status_code == 200
        assert sensitive.json()["error_code"] == "WEB_SUPPORT_ATTACHMENT_CONTENT_RESTRICTED"

        payment_case = create_case(
            owner, csrf, key="support-evidence-payment-case-0001", category="payment_topup",
        )
        payment = attach(
            owner, csrf, payment_case["id"], safe_asset["id"], revision=1,
            key="support-evidence-payment-link-0001",
        )
        assert payment.status_code == 200
        assert payment.json()["error_code"] == "WEB_SUPPORT_ATTACHMENT_PAYMENT_CATEGORY_BLOCKED"

        # Type/size guards run before any private blob read. Seed only safe
        # metadata fixtures here so this test proves the contract without
        # inventing a second raw upload path in Support Desk.
        with sqlite3.connect(tmp_path / "support-evidence.db") as conn:
            account_id = conn.execute(
                "SELECT id FROM web_accounts WHERE email='evidence-guard-owner@example.com'"
            ).fetchone()[0]
            unsupported_asset_id = str(uuid.uuid4())
            oversized_asset_id = str(uuid.uuid4())
            for asset_id, display_name, extension, content_type, byte_size in (
                (unsupported_asset_id, "Tài liệu không được phép", ".pdf", "application/pdf", 1024),
                (oversized_asset_id, "Log quá kích thước", ".txt", "text/plain", 5 * 1024 * 1024 + 1),
            ):
                conn.execute(
                    """INSERT INTO web_asset_files
                       (id, account_id, project_id, display_name, original_filename, extension, content_type,
                        byte_size, sha256, storage_key, state, created_at, updated_at, archived_at)
                       VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, NULL)""",
                    (
                        asset_id, account_id, display_name, f"fixture{extension}", extension, content_type,
                        byte_size, "0" * 64, f"fixture/{asset_id}.blob",
                        "2026-07-16T00:00:00+00:00", "2026-07-16T00:00:00+00:00",
                    ),
                )
            conn.commit()

        unsupported = attach(
            owner, csrf, case["id"], unsupported_asset_id, revision=1,
            key="support-evidence-guard-type-0001",
        )
        assert unsupported.status_code == 200
        assert unsupported.json()["error_code"] == "WEB_SUPPORT_ATTACHMENT_TYPE_NOT_ALLOWED"
        oversized = attach(
            owner, csrf, case["id"], oversized_asset_id, revision=1,
            key="support-evidence-guard-size-0001",
        )
        assert oversized.status_code == 200
        assert oversized.json()["error_code"] == "WEB_SUPPORT_ATTACHMENT_SIZE_LIMIT"

        limit_case = create_case(owner, csrf, key="support-evidence-limit-case-0001")
        revision = 1
        for index in range(3):
            candidate = upload_text(
                owner, csrf, key=f"support-evidence-limit-asset-000{index + 1}",
                content=f"safe support trace {index}".encode("utf-8"),
                name=f"safe-{index}.txt",
            )
            accepted = attach(
                owner, csrf, limit_case["id"], candidate["id"], revision=revision,
                key=f"support-evidence-limit-link-000{index + 1}",
            )
            assert accepted.status_code == 200, accepted.text
            assert accepted.json()["ok"] is True
            revision += 1
        fourth = upload_text(
            owner, csrf, key="support-evidence-limit-asset-0004",
            content=b"fourth safe support trace", name="safe-fourth.txt",
        )
        limit = attach(
            owner, csrf, limit_case["id"], fourth["id"], revision=revision,
            key="support-evidence-limit-link-0004",
        )
        assert limit.status_code == 200
        assert limit.json()["error_code"] == "WEB_SUPPORT_ATTACHMENT_LIMIT"

    with make_client(tmp_path, monkeypatch) as foreign:
        foreign_csrf = register_and_login(foreign, "evidence-foreign@example.com", display_name="Evidence Foreign")
        foreign_asset = upload_text(
            foreign, foreign_csrf, key="support-evidence-foreign-asset-0001", content=b"foreign asset"
        )

    with make_client(tmp_path, monkeypatch) as owner_again:
        owner_csrf = login(owner_again, "evidence-guard-owner@example.com")
        foreign_link = attach(
            owner_again, owner_csrf, case["id"], foreign_asset["id"], revision=1,
            key="support-evidence-foreign-link-0001",
        )
        assert foreign_link.status_code == 200
        assert foreign_link.json()["error_code"] == "WEB_SUPPORT_ATTACHMENT_ASSET_NOT_AVAILABLE"
