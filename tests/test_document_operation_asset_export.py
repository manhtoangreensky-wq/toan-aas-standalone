"""RED contract for Document Operation → private Asset Vault export."""

from __future__ import annotations

from io import BytesIO
import hashlib
import importlib
from pathlib import Path
import sqlite3
import sys

from docx import Document
from fastapi.testclient import TestClient
from pypdf import PdfWriter


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


def make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "document-operation-asset-export.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "document-operation-asset-export-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ROOT", str(tmp_path / "private-document-outputs"))
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB", "20")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_IMAGE_TO_PDF_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PDF_TO_IMAGES_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PDF_TO_WORD_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OCR_PDF_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_PDF_OCR_WORD_ENABLED", "false")
    monkeypatch.setenv("WEBAPP_IMAGE_OPERATIONS_ENABLED", "false")
    monkeypatch.delenv("WEBAPP_PROJECT_PACKAGE_ENABLED", raising=False)
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
            "display_name": "Document Export Owner",
        },
    )
    assert registered.status_code == 200, registered.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200, login.text
    return login.json()["data"]["csrf_token"]


def pdf_bytes(page_count: int = 3) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=144, height=144)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def upload_pdf(client: TestClient, csrf: str, *, key: str) -> dict:
    response = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
        data={"display_name": "PDF nguồn riêng tư"},
        files={"file": ("source.pdf", pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["asset"]


def completed_pdf_split(client: TestClient, csrf: str, *, key_suffix: str = "0001") -> dict:
    source = upload_pdf(client, csrf, key=f"document-export-source-{key_suffix}")
    response = client.post(
        "/api/v1/document-operations/pdf-split",
        headers={"X-CSRF-Token": csrf},
        json={
            "source_asset_id": source["id"],
            "page_range": "1-2",
            "idempotency_key": f"document-export-split-{key_suffix}",
        },
    )
    assert response.status_code == 200, response.text
    operation = response.json()["data"]["operation"]
    assert operation["state"] == "completed"
    assert operation["kind"] == "pdf_split"
    return operation


def asset_count(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM web_asset_files").fetchone()[0])


def export_operation(client: TestClient, csrf: str, operation_id: str, key: str):
    return client.post(
        f"/api/v1/document-operations/{operation_id}/export-to-asset-vault",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": key},
    )


def operation_storage_key(db_path: Path, operation_id: str) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT storage_key FROM web_document_operations WHERE id=?",
            (operation_id,),
        ).fetchone()
    assert row and row[0]
    return str(row[0])


def docx_bytes() -> bytes:
    document = Document()
    document.add_paragraph("Tài liệu DOCX đã được xác minh trước khi export.")
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def seed_verified_completed_operation(
    tmp_path: Path,
    *,
    email: str,
    source_asset_id: str,
    operation_id: str,
    kind: str,
    extension: str,
    content_type: str,
    original_filename: str,
    payload: bytes,
) -> None:
    db_path = tmp_path / "document-operation-asset-export.db"
    storage_key = f"outputs/{operation_id.replace('-', '')}{extension}"
    output = tmp_path / "private-document-outputs" / storage_key
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    with sqlite3.connect(db_path) as conn:
        account_id = conn.execute("SELECT id FROM web_accounts WHERE email=?", (email,)).fetchone()[0]
        now = conn.execute("SELECT updated_at FROM web_accounts WHERE id=?", (account_id,)).fetchone()[0]
        conn.execute(
            """INSERT INTO web_document_operations
               (id, account_id, source_asset_id, project_id, kind, state, idempotency_key,
                request_fingerprint, source_sha256, source_byte_size, source_count,
                requested_page_range, selected_start_page, selected_end_page, source_page_count,
                output_page_count, storage_key, original_filename, content_type, byte_size,
                sha256, failure_code, created_at, queued_at, started_at, completed_at, updated_at)
               VALUES (?, ?, ?, NULL, ?, 'completed', ?, ?, ?, 1, 1,
                       '', NULL, NULL, 1, 1, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)""",
            (
                operation_id,
                account_id,
                source_asset_id,
                kind,
                f"route-seeded-{operation_id}",
                digest,
                digest,
                storage_key,
                original_filename,
                content_type,
                len(payload),
                digest,
                now,
                now,
                now,
                now,
                now,
            ),
        )
        conn.commit()


def test_verified_seeded_docx_and_text_outputs_export_through_real_asset_vault_finalization(
    tmp_path,
    monkeypatch,
) -> None:
    email = "document-export-docx-txt-route@example.com"
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, email)
        source = upload_pdf(client, csrf, key="document-export-docx-txt-source-0001")
        cases = (
            (
                "40000000-0000-4000-8000-000000000001",
                "pdf_to_word_text",
                ".docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "toan-aas-pdf-text.docx",
                docx_bytes(),
            ),
            (
                "40000000-0000-4000-8000-000000000002",
                "image_ocr",
                ".txt",
                "text/plain; charset=utf-8",
                "toan-aas-image-ocr.txt",
                "Nội dung OCR UTF-8 đã xác minh.\n".encode("utf-8"),
            ),
        )
        for index, (operation_id, kind, extension, content_type, filename, payload) in enumerate(cases, start=1):
            seed_verified_completed_operation(
                tmp_path,
                email=email,
                source_asset_id=source["id"],
                operation_id=operation_id,
                kind=kind,
                extension=extension,
                content_type=content_type,
                original_filename=filename,
                payload=payload,
            )

            exported = export_operation(
                client,
                csrf,
                operation_id,
                f"document-export-docx-txt-route-{index:04d}",
            )

            assert exported.status_code == 200, exported.text
            body = exported.json()
            assert body["ok"] is True
            assert body["status"] == "completed"
            asset = body["data"]["asset"]
            assert asset["extension"] == extension
            assert asset["content_type"] == content_type
            downloaded = client.get(f"/api/v1/asset-vault/{asset['id']}/download")
            assert downloaded.status_code == 200, downloaded.text
            assert downloaded.content == payload


def assert_guarded_without_asset(response, db_path: Path, expected_count: int) -> None:
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is False
    assert body["status"] == "guarded"
    assert "asset" not in body.get("data", {})
    assert asset_count(db_path) == expected_count


def test_completed_pdf_operation_exports_to_a_distinct_private_asset(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "document-export-owner@example.com")
        operation = completed_pdf_split(client, csrf)
        original = client.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert original.status_code == 200, original.text
        assert original.headers["content-type"].startswith("application/pdf")
        assert "toan-aas-pdf-pages-1-2.pdf" in original.headers["content-disposition"]

        exported = client.post(
            f"/api/v1/document-operations/{operation['id']}/export-to-asset-vault",
            headers={"X-CSRF-Token": csrf, "Idempotency-Key": "document-export-copy-0001"},
        )

        assert exported.status_code == 200, exported.text
        body = exported.json()
        assert body["ok"] is True
        asset = body["data"]["asset"]
        assert asset["original_filename"] == "toan-aas-pdf-split.pdf"
        assert asset["extension"] == ".pdf"
        assert asset["content_type"] == "application/pdf"
        assert asset["byte_size"] == len(original.content)
        assert {"storage_key", "sha256", "account_id", "source_asset_id"}.isdisjoint(asset)
        saved = client.get(f"/api/v1/asset-vault/{asset['id']}/download")
        assert saved.status_code == 200, saved.text
        assert saved.content == original.content
        assert asset_count(tmp_path / "document-operation-asset-export.db") == 2


def test_document_export_replay_security_and_source_lifecycle_are_owner_scoped(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "document-export-replay-owner@example.com")
        operation = completed_pdf_split(client, csrf)
        db_path = tmp_path / "document-operation-asset-export.db"
        before = asset_count(db_path)

        missing_csrf = client.post(
            f"/api/v1/document-operations/{operation['id']}/export-to-asset-vault",
            headers={"Idempotency-Key": "document-export-missing-csrf-0001"},
        )
        assert missing_csrf.status_code == 403
        header_only = client.post(
            f"/api/v1/document-operations/{operation['id']}/export-to-asset-vault",
            headers={"X-CSRF-Token": csrf},
        )
        assert header_only.status_code == 422
        assert asset_count(db_path) == before

        with make_client(tmp_path, monkeypatch) as foreign:
            foreign_csrf = register_and_login(foreign, "document-export-foreign@example.com")
            foreign_result = export_operation(
                foreign, foreign_csrf, operation["id"], "document-export-foreign-0001"
            )
            assert_guarded_without_asset(foreign_result, db_path, before)

        original = client.get(f"/api/v1/document-operations/{operation['id']}/download")
        assert original.status_code == 200, original.text
        first = export_operation(client, csrf, operation["id"], "document-export-replay-0001")
        assert first.status_code == 200, first.text
        first_asset = first.json()["data"]["asset"]
        replay = export_operation(client, csrf, operation["id"], "document-export-replay-0001")
        assert replay.status_code == 200, replay.text
        assert replay.json()["data"]["asset"]["id"] == first_asset["id"]
        assert asset_count(db_path) == before + 1
        assert client.get(f"/api/v1/document-operations/{operation['id']}/download").content == original.content

        second = completed_pdf_split(client, csrf, key_suffix="0002")
        rebind = export_operation(client, csrf, second["id"], "document-export-replay-0001")
        assert rebind.status_code == 409
        assert asset_count(db_path) == before + 2


def test_document_export_guards_ineligible_tampered_and_failed_storage_lifecycle(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "document-export-guard-owner@example.com")
        operation = completed_pdf_split(client, csrf)
        db_path = tmp_path / "document-operation-asset-export.db"
        before = asset_count(db_path)

        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_document_operations SET state='processing' WHERE id=?", (operation["id"],))
            conn.commit()
        assert_guarded_without_asset(
            export_operation(client, csrf, operation["id"], "document-export-incomplete-0001"),
            db_path,
            before,
        )

        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_document_operations SET state='completed', kind='pdf_to_images' WHERE id=?", (operation["id"],))
            conn.commit()
        assert_guarded_without_asset(
            export_operation(client, csrf, operation["id"], "document-export-pdf-images-0001"),
            db_path,
            before,
        )

        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE web_document_operations SET kind='pdf_split' WHERE id=?", (operation["id"],))
            conn.commit()
        (tmp_path / "private-document-outputs" / operation_storage_key(db_path, operation["id"])).write_bytes(b"tampered")
        assert_guarded_without_asset(
            export_operation(client, csrf, operation["id"], "document-export-tampered-0001"),
            db_path,
            before,
        )

        clean_operation = completed_pdf_split(client, csrf, key_suffix="0002")
        assets = importlib.import_module("copyfast_assets")
        # Storage-boundary simulation: finalization does not commit an asset
        # and its receipt is unavailable. This is deliberately not a mocked
        # successful export; the HTTP layer must not turn it into success.
        monkeypatch.setattr(assets, "finalize_document_operation_asset_export", lambda **_kwargs: None)
        monkeypatch.setattr(assets, "get_document_operation_asset_export_receipt", lambda **_kwargs: None)
        no_receipt = export_operation(client, csrf, clean_operation["id"], "document-export-no-receipt-0001")
        assert_guarded_without_asset(no_receipt, db_path, before + 1)


def test_document_export_route_is_declared_after_detail_and_before_download() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "copyfast_document_operations.py"
    ).read_text(encoding="utf-8")
    detail = source.index('@router.get("/{operation_id}")')
    export = source.index('@router.post("/{operation_id}/export-to-asset-vault")')
    download = source.index('@router.get("/{operation_id}/download")')
    assert detail < export < download
