"""Failure-domain regression for sealed Document Operation export sources."""

from __future__ import annotations

from io import BytesIO
import errno
import hashlib
import importlib
from pathlib import Path
import sqlite3
import sys

from pypdf import PdfWriter


ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"
SOURCE_ASSET_ID = "22222222-2222-4222-8222-222222222222"
OPERATION_ID = "30000000-0000-4000-8000-000000000020"


def load_modules(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "document-operation-export-failure-domains.db"))
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ROOT", str(tmp_path / "private-document-outputs"))
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_MAX_OUTPUT_MB", "20")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "false")
    monkeypatch.delenv("WEBAPP_PROJECT_PACKAGE_ENABLED", raising=False)
    for name in ("APP_ENV", "ENVIRONMENT", "RAILWAY_ENVIRONMENT", "RAILWAY_VOLUME_MOUNT_PATH"):
        monkeypatch.delenv(name, raising=False)
    for name in ("copyfast_document_operations", "copyfast_auth", "copyfast_db"):
        sys.modules.pop(name, None)
    db = importlib.import_module("copyfast_db")
    operations = importlib.import_module("copyfast_document_operations")
    db.ensure_copyfast_schema()
    return db, operations


def pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=144, height=144)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def seed_completed_pdf_operation(db) -> Path:
    payload = pdf_bytes()
    root = db.document_operations_directory()
    storage_key = f"outputs/{OPERATION_ID.replace('-', '')}.pdf"
    output = root / storage_key
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache,
                is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, NULL, 'user', 1, 1, ?, ?)""",
            (ACCOUNT_ID, "export-failure-domain@example.com", "not-a-login-hash", "Export Source", now, now),
        )
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension,
                content_type, byte_size, sha256, storage_key, state, lifecycle_revision,
                created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, '.pdf', 'application/pdf', 1, ?, ?, 'active', 1, ?, ?, NULL)""",
            (SOURCE_ASSET_ID, ACCOUNT_ID, "Nguồn", "source.pdf", "a" * 64, "objects/" + "1" * 32 + ".blob", now, now),
        )
        conn.execute(
            """INSERT INTO web_document_operations
               (id, account_id, source_asset_id, project_id, kind, state, idempotency_key,
                request_fingerprint, source_sha256, source_byte_size, requested_page_range,
                selected_start_page, selected_end_page, source_page_count, output_page_count,
                storage_key, original_filename, content_type, byte_size, sha256, failure_code,
                created_at, queued_at, started_at, completed_at, updated_at)
               VALUES (?, ?, ?, NULL, 'pdf_split', 'completed', ?, ?, ?, ?, ?, 1, 1, 1, 1, ?, ?, ?, ?, ?, NULL,
                       ?, ?, ?, ?, ?)""",
            (
                OPERATION_ID,
                ACCOUNT_ID,
                SOURCE_ASSET_ID,
                f"document-export-{OPERATION_ID}",
                "b" * 64,
                "c" * 64,
                1,
                "",
                storage_key,
                "toan-aas-pdf-pages-1-1.pdf",
                "application/pdf",
                len(payload),
                hashlib.sha256(payload).hexdigest(),
                now,
                now,
                now,
                now,
                now,
            ),
        )
    return output


def seed_completed_docx_operation(db, operations) -> Path:
    payload = b"not-read-because-the-shared-docx-validator-is-unavailable"
    root = db.document_operations_directory()
    storage_key = f"outputs/{OPERATION_ID.replace('-', '')}.docx"
    output = root / storage_key
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    extension, content_type, _ = operations._output_spec(
        operations.PDF_TO_WORD_KIND,
        output_page_count=1,
        selected_start_page=None,
        selected_end_page=None,
    )
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache,
                is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, NULL, 'user', 1, 1, ?, ?)""",
            (ACCOUNT_ID, "export-docx-failure-domain@example.com", "not-a-login-hash", "Export Source", now, now),
        )
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension,
                content_type, byte_size, sha256, storage_key, state, lifecycle_revision,
                created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, '.pdf', 'application/pdf', 1, ?, ?, 'active', 1, ?, ?, NULL)""",
            (SOURCE_ASSET_ID, ACCOUNT_ID, "Nguồn", "source.pdf", "a" * 64, "objects/" + "2" * 32 + ".blob", now, now),
        )
        conn.execute(
            """INSERT INTO web_document_operations
               (id, account_id, source_asset_id, project_id, kind, state, idempotency_key,
                request_fingerprint, source_sha256, source_byte_size, requested_page_range,
                selected_start_page, selected_end_page, source_page_count, output_page_count,
                storage_key, original_filename, content_type, byte_size, sha256, failure_code,
                created_at, queued_at, started_at, completed_at, updated_at)
               VALUES (?, ?, ?, NULL, ?, 'completed', ?, ?, ?, ?, ?, NULL, NULL, 1, 1, ?, ?, ?, ?, ?, NULL,
                       ?, ?, ?, ?, ?)""",
            (
                OPERATION_ID,
                ACCOUNT_ID,
                SOURCE_ASSET_ID,
                operations.PDF_TO_WORD_KIND,
                f"document-export-{OPERATION_ID}",
                "b" * 64,
                "c" * 64,
                1,
                "",
                storage_key,
                operations._completed_operation_output_filename(
                    operations.PDF_TO_WORD_KIND,
                    selected_start_page=None,
                    selected_end_page=None,
                ),
                content_type,
                len(payload),
                hashlib.sha256(payload).hexdigest(),
                now,
                now,
                now,
                now,
                now,
            ),
        )
    assert extension == ".docx"
    return output


def operation_state(tmp_path: Path) -> str:
    with sqlite3.connect(tmp_path / "document-operation-export-failure-domains.db") as conn:
        row = conn.execute("SELECT state FROM web_document_operations WHERE id=?", (OPERATION_ID,)).fetchone()
    assert row is not None
    return str(row[0])


def test_unexpected_artifact_validator_runtime_error_is_destination_failure_without_lifecycle_demotion(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    seed_completed_pdf_operation(db)

    def unexpected_artifact_validator(*args, **kwargs):
        raise RuntimeError("unexpected PDF parser runtime failure")

    monkeypatch.setattr(operations, "_validate_document_operation_export_artifact", unexpected_artifact_validator)

    result = operations.open_document_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.DESTINATION
    assert result.is_source_integrity_failure is False
    assert operations.mark_document_operation_export_source_unavailable(result) is False
    assert operation_state(tmp_path) == "completed"


def test_pdf_parser_runtime_error_is_destination_failure_without_lifecycle_demotion(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    seed_completed_pdf_operation(db)

    class ExplodingPdfReader:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("unexpected PDF parser runtime failure")

    monkeypatch.setattr(operations, "_pdf_classes", lambda: (ExplodingPdfReader, object))

    result = operations.open_document_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.DESTINATION
    assert result.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_STORAGE_UNAVAILABLE"
    assert result.is_source_integrity_failure is False
    assert operations.mark_document_operation_export_source_unavailable(result) is False
    assert operation_state(tmp_path) == "completed"


def test_shared_docx_validator_runtime_error_is_destination_failure_without_lifecycle_demotion(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    seed_completed_docx_operation(db, operations)
    assets = importlib.import_module("copyfast_assets")

    def exploding_docx_validator(stream) -> bool:
        raise RuntimeError("unexpected DOCX validator runtime failure")

    monkeypatch.setattr(assets, "_document_operation_docx_stream_is_safe", exploding_docx_validator)

    result = operations.open_document_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.DESTINATION
    assert result.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_STORAGE_UNAVAILABLE"
    assert result.is_source_integrity_failure is False
    assert operations.mark_document_operation_export_source_unavailable(result) is False
    assert operation_state(tmp_path) == "completed"


def test_transient_final_output_open_is_destination_failure_without_lifecycle_demotion(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    output = seed_completed_pdf_operation(db)
    real_open = operations.os.open
    had_directory_fd_support = operations._operation_directory_fd_supported()
    used_descriptor_relative_output_open = False

    def transient_final_output_open(path, flags, *args, **kwargs):
        nonlocal used_descriptor_relative_output_open
        is_descriptor_relative_output = path == output.name and kwargs.get("dir_fd") is not None
        if is_descriptor_relative_output:
            used_descriptor_relative_output_open = True
        if Path(path) == output or is_descriptor_relative_output:
            raise OSError("temporary output storage failure")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(operations.os, "open", transient_final_output_open)
    if had_directory_fd_support:
        monkeypatch.setattr(
            operations.os,
            "supports_dir_fd",
            set(operations.os.supports_dir_fd) | {transient_final_output_open},
        )

    result = operations.open_document_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.DESTINATION
    assert result.is_source_integrity_failure is False
    assert operations.mark_document_operation_export_source_unavailable(result) is False
    assert operation_state(tmp_path) == "completed"
    assert used_descriptor_relative_output_open is had_directory_fd_support


def test_transient_private_directory_open_is_destination_failure_without_lifecycle_demotion(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    output = seed_completed_pdf_operation(db)
    private_root = output.parent.parent
    real_open = operations.os.open

    monkeypatch.setattr(operations, "_operation_directory_fd_supported", lambda: True)
    monkeypatch.setattr(operations.os, "O_DIRECTORY", getattr(operations.os, "O_DIRECTORY", 0) or 0x10000, raising=False)
    monkeypatch.setattr(operations.os, "O_NOFOLLOW", getattr(operations.os, "O_NOFOLLOW", 0) or 0x20000, raising=False)

    def transient_private_root_open(path, flags, *args, **kwargs):
        if Path(path) == private_root:
            raise OSError(errno.EIO, "temporary private output storage failure")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(operations.os, "open", transient_private_root_open)

    result = operations.open_document_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.DESTINATION
    assert result.is_source_integrity_failure is False
    assert operations.mark_document_operation_export_source_unavailable(result) is False
    assert operation_state(tmp_path) == "completed"


def test_eloop_final_output_open_is_source_integrity_for_export_opt_in_while_legacy_returns_none(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    output = seed_completed_pdf_operation(db)
    real_open = operations.os.open
    had_directory_fd_support = operations._operation_directory_fd_supported()

    def final_output_symlink_race(path, flags, *args, **kwargs):
        is_descriptor_relative_output = path == output.name and kwargs.get("dir_fd") is not None
        if Path(path) == output or is_descriptor_relative_output:
            raise OSError(errno.ELOOP, "output became a symlink before O_NOFOLLOW open")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(operations.os, "open", final_output_symlink_race)
    if had_directory_fd_support:
        monkeypatch.setattr(
            operations.os,
            "supports_dir_fd",
            set(operations.os.supports_dir_fd) | {final_output_symlink_race},
        )

    # On runtimes without dir_fd this is a controlled error-classification
    # test; it does not claim that the platform executed POSIX nofollow I/O.
    legacy_stream = operations._open_verified_operation_output(
        output,
        expected_bytes=len(output.read_bytes()),
        expected_digest=hashlib.sha256(output.read_bytes()).hexdigest(),
    )
    assert legacy_stream is None

    result = operations.open_document_operation_export_source(
        operation_id=OPERATION_ID,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.SOURCE_INTEGRITY
    assert result.is_source_integrity_failure is True
    assert operation_state(tmp_path) == "completed"
