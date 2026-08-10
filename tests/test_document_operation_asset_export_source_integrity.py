"""Contract tests for the sealed Document Operation export source boundary."""

from __future__ import annotations

from io import BytesIO
import hashlib
import importlib
import os
from pathlib import Path
import sqlite3
import stat
import sys

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


def make_client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "document-operation-export-source.db"))
    monkeypatch.setenv("WEB_SESSION_SECRET", "document-operation-export-source-session-secret")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ROOT", str(tmp_path / "private-document-outputs"))
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB", "20")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB", "100")
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


def pdf_bytes(page_count: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=144, height=144)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def register_and_login(client: TestClient, email: str) -> str:
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery-staple",
            "display_name": "Document export source owner",
        },
    )
    assert registered.status_code == 200, registered.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert login.status_code == 200, login.text
    return login.json()["data"]["csrf_token"]


def completed_pdf_split(client: TestClient, csrf: str) -> tuple[dict, bytes]:
    uploaded = client.post(
        "/api/v1/asset-vault/upload",
        headers={"X-CSRF-Token": csrf, "Idempotency-Key": "document-export-source-upload-0001"},
        data={"display_name": "Nguồn PDF riêng tư"},
        files={"file": ("source.pdf", pdf_bytes(), "application/pdf")},
    )
    assert uploaded.status_code == 200, uploaded.text
    source = uploaded.json()["data"]["asset"]
    created = client.post(
        "/api/v1/document-operations/pdf-split",
        headers={"X-CSRF-Token": csrf},
        json={
            "source_asset_id": source["id"],
            "page_range": "1-2",
            "idempotency_key": "document-export-source-split-0001",
        },
    )
    assert created.status_code == 200, created.text
    operation = created.json()["data"]["operation"]
    assert operation["state"] == "completed"
    downloaded = client.get(f"/api/v1/document-operations/{operation['id']}/download")
    assert downloaded.status_code == 200, downloaded.text
    return operation, downloaded.content


def operation_owner_and_storage(db_path: Path, operation_id: str) -> tuple[str, str]:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT account_id, storage_key FROM web_document_operations WHERE id=?",
            (operation_id,),
        ).fetchone()
    assert row
    return str(row[0]), str(row[1])


def file_symlink_or_emulate_final_resolution(link: Path, target: Path, operations, monkeypatch) -> None:
    """Create the hostile final link, or model it on Windows without link rights.

    The fallback is deliberately confined to the name-resolution boundary: it
    reproduces the old ``Path.resolve()`` behavior without weakening the
    descriptor-pinned source test on hosts where a real symlink is available.
    """

    try:
        link.symlink_to(target)
    except OSError as exc:
        if getattr(exc, "winerror", None) != 1314:
            raise
        real_resolve = operations.Path.resolve

        def resolve_internal_final_symlink(path: Path, *args, **kwargs) -> Path:
            if path == link:
                return target
            return real_resolve(path, *args, **kwargs)

        real_lstat = operations.os.lstat

        def lstat_internal_final_symlink(path, *args, **kwargs):
            if Path(path) == link:
                target_metadata = real_lstat(target, *args, **kwargs)
                return os.stat_result((stat.S_IFLNK | 0o777, *tuple(target_metadata)[1:]))
            return real_lstat(path, *args, **kwargs)

        monkeypatch.setattr(operations.Path, "resolve", resolve_internal_final_symlink)
        monkeypatch.setattr(operations.os, "lstat", lstat_internal_final_symlink)


def test_completed_pdf_export_source_is_descriptor_pinned_and_server_derived(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "document-export-source-owner@example.com")
        operation, expected_body = completed_pdf_split(client, csrf)
        db_path = tmp_path / "document-operation-export-source.db"
        account_id, storage_key = operation_owner_and_storage(db_path, operation["id"])
        operations = importlib.import_module("copyfast_document_operations")

        result = operations.open_document_operation_export_source(
            operation_id=operation["id"],
            account_id=account_id,
        )

        assert result.failure is None
        assert result.source is not None
        source = result.source
        try:
            assert source.account_id == account_id
            assert source.operation_id == operation["id"]
            assert source.kind == "pdf_split"
            assert source.project_id is None
            assert source.original_filename == "toan-aas-pdf-split.pdf"
            assert source.extension == ".pdf"
            assert source.content_type == "application/pdf"
            assert source.byte_size == len(expected_body)
            assert source.sha256 == hashlib.sha256(expected_body).hexdigest()
            assert source.stream.read() == expected_body
            assert storage_key not in repr(source)
            assert source.sha256 not in repr(source)
            assert storage_key not in repr(result)
        finally:
            result.close()


def test_export_source_rejects_unsupported_kind_and_tampered_digest_without_storage_leak(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "document-export-source-negative@example.com")
        operation, _expected_body = completed_pdf_split(client, csrf)
        db_path = tmp_path / "document-operation-export-source.db"
        account_id, storage_key = operation_owner_and_storage(db_path, operation["id"])
        operations = importlib.import_module("copyfast_document_operations")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_document_operations SET kind='pdf_to_images' WHERE id=?",
                (operation["id"],),
            )
            conn.commit()

        unsupported = operations.open_document_operation_export_source(
            operation_id=operation["id"],
            account_id=account_id,
        )
        assert unsupported.source is None
        assert unsupported.failure is not None
        assert unsupported.failure.domain.value == "precondition"
        assert unsupported.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_NOT_ELIGIBLE"
        assert storage_key not in repr(unsupported)
        assert operations.mark_document_operation_export_source_unavailable(unsupported) is False

        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_document_operations SET kind='pdf_split', sha256=? WHERE id=?",
                ("0" * 64, operation["id"]),
            )
            conn.commit()

        tampered = operations.open_document_operation_export_source(
            operation_id=operation["id"],
            account_id=account_id,
        )
        assert tampered.source is None
        assert tampered.failure is not None
        assert tampered.failure.domain.value == "source_integrity"
        assert tampered.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_SOURCE_UNAVAILABLE"
        assert storage_key not in repr(tampered)
        assert "0" * 64 not in repr(tampered)


def test_source_integrity_failure_requires_explicit_unavailable_transition(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "document-export-source-transition@example.com")
        operation, _expected_body = completed_pdf_split(client, csrf)
        db_path = tmp_path / "document-operation-export-source.db"
        account_id, _storage_key = operation_owner_and_storage(db_path, operation["id"])
        operations = importlib.import_module("copyfast_document_operations")
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_document_operations SET sha256=? WHERE id=?",
                ("f" * 64, operation["id"]),
            )
            conn.commit()

        result = operations.open_document_operation_export_source(
            operation_id=operation["id"],
            account_id=account_id,
        )
        assert result.is_source_integrity_failure is True
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT state FROM web_document_operations WHERE id=?",
                (operation["id"],),
            ).fetchone()[0] == "completed"

        assert operations.mark_document_operation_export_source_unavailable(result) is True
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT state FROM web_document_operations WHERE id=?",
                (operation["id"],),
            ).fetchone()[0] == "unavailable"


def test_export_source_rejects_pdf_bytes_after_terminal_eof_even_when_metadata_is_resealed(tmp_path, monkeypatch) -> None:
    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "document-export-source-trailing-pdf@example.com")
        operation, original = completed_pdf_split(client, csrf)
        db_path = tmp_path / "document-operation-export-source.db"
        account_id, storage_key = operation_owner_and_storage(db_path, operation["id"])
        payload = original + b"unexpected trailing bytes"
        output = tmp_path / "private-document-outputs" / storage_key
        output.write_bytes(payload)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE web_document_operations SET byte_size=?, sha256=? WHERE id=?",
                (len(payload), hashlib.sha256(payload).hexdigest(), operation["id"]),
            )
            conn.commit()
        operations = importlib.import_module("copyfast_document_operations")

        result = operations.open_document_operation_export_source(
            operation_id=operation["id"],
            account_id=account_id,
        )

        assert result.source is None
        assert result.failure is not None
        assert result.failure.domain is operations.DocumentOperationExportFailureDomain.SOURCE_INTEGRITY
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM web_document_operation_asset_exports WHERE operation_id=?",
                (operation["id"],),
            ).fetchone()[0] == 0


def test_export_source_rejects_same_hash_internal_final_output_symlink(tmp_path, monkeypatch) -> None:
    """The sealed storage key must remain the final nofollow-opened basename."""

    with make_client(tmp_path, monkeypatch) as client:
        csrf = register_and_login(client, "document-export-source-symlink@example.com")
        operation, expected_body = completed_pdf_split(client, csrf)
        db_path = tmp_path / "document-operation-export-source.db"
        account_id, storage_key = operation_owner_and_storage(db_path, operation["id"])
        root = tmp_path / "private-document-outputs"
        output = root / storage_key
        same_hash_target = output.parent / "same-hash-target.pdf"
        same_hash_target.write_bytes(expected_body)
        output.unlink()
        operations = importlib.import_module("copyfast_document_operations")
        file_symlink_or_emulate_final_resolution(output, same_hash_target, operations, monkeypatch)

        result = operations.open_document_operation_export_source(
            operation_id=operation["id"],
            account_id=account_id,
        )

        assert result.source is None
        assert result.failure is not None
        assert result.failure.domain is operations.DocumentOperationExportFailureDomain.SOURCE_INTEGRITY
        assert result.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_SOURCE_UNAVAILABLE"
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT state FROM web_document_operations WHERE id=?",
                (operation["id"],),
            ).fetchone()[0] == "completed"
        assert operations.mark_document_operation_export_source_unavailable(result) is True
        with sqlite3.connect(db_path) as conn:
            assert conn.execute(
                "SELECT state FROM web_document_operations WHERE id=?",
                (operation["id"],),
            ).fetchone()[0] == "unavailable"
