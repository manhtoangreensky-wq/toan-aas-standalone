"""Real-file contracts for Document Operation export sources."""

from __future__ import annotations

from io import BytesIO
import hashlib
import importlib
from pathlib import Path
import sqlite3
import struct
import sys
import zlib
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from docx import Document
from PIL import Image, ImageFile
from pypdf import PdfWriter


ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"
SOURCE_ASSET_ID = "22222222-2222-4222-8222-222222222222"
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
UTF8_TEXT_MEDIA_TYPE = "text/plain; charset=utf-8"
REAL_OUTPUT_FILENAMES = {
    "pdf_to_images": "toan-aas-pdf-pages.zip",
    "pdf_merge": "toan-aas-merged-pdf.pdf",
    "pdf_optimize": "toan-aas-optimized-pdf.pdf",
    "image_to_pdf": "toan-aas-images.pdf",
    "pdf_to_word_text": "toan-aas-pdf-text.docx",
    "pdf_ocr_word": "toan-aas-pdf-ocr.docx",
    "image_ocr": "toan-aas-image-ocr.txt",
    "pdf_ocr": "toan-aas-pdf-ocr.txt",
}


def load_modules(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "document-operation-export-docx-txt.db"))
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


def valid_docx_bytes() -> bytes:
    document = Document()
    document.add_paragraph("Nội dung DOCX riêng tư hợp lệ.")
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def valid_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=144, height=144)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def unsafe_docx_bytes(unsafe_case: str) -> bytes:
    source = BytesIO(valid_docx_bytes())
    rebuilt = BytesIO()
    with ZipFile(source, "r") as archive, ZipFile(rebuilt, "w", compression=ZIP_DEFLATED) as output:
        for info in archive.infolist():
            output.writestr(info, archive.read(info.filename))
        if unsafe_case == "macro":
            output.writestr("word/vbaProject.bin", b"macro payload")
        elif unsafe_case == "external":
            output.writestr(
                "word/_rels/export-source.rels",
                b'<Relationships><Relationship Target="https://example.invalid" TargetMode="External"/></Relationships>',
            )
        elif unsafe_case == "traversal":
            output.writestr("../outside.txt", b"path traversal")
        else:
            raise AssertionError(f"unknown unsafe DOCX fixture: {unsafe_case}")
    return rebuilt.getvalue()


def rewritten_docx_bytes(
    *,
    omit: frozenset[str] = frozenset(),
    replacements: dict[str, bytes] | None = None,
) -> bytes:
    source = BytesIO(valid_docx_bytes())
    rebuilt = BytesIO()
    replacements = replacements or {}
    with ZipFile(source, "r") as archive, ZipFile(rebuilt, "w", compression=ZIP_DEFLATED) as output:
        for info in archive.infolist():
            if info.filename in omit:
                continue
            output.writestr(info, replacements.get(info.filename, archive.read(info.filename)))
    return rebuilt.getvalue()


def underreported_eocd_docx_bytes() -> bytes:
    payload = bytearray(valid_docx_bytes())
    eocd = payload.rfind(b"PK\x05\x06")
    assert eocd >= 0
    entries = struct.unpack_from("<H", payload, eocd + 10)[0]
    assert entries > 1
    struct.pack_into("<H", payload, eocd + 8, entries - 1)
    struct.pack_into("<H", payload, eocd + 10, entries - 1)
    return bytes(payload)


def real_zip_bytes() -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("page-001.png", b"real-pdf-page-fixture")
    return stream.getvalue()


def real_png_bytes() -> bytes:
    image = Image.new("RGB", (8, 6), color=(22, 163, 183))
    stream = BytesIO()
    try:
        image.save(stream, format="PNG")
        return stream.getvalue()
    finally:
        image.close()


def png_with_exif_chunk() -> bytes:
    payload = real_png_bytes()
    offset = len(b"\x89PNG\r\n\x1a\n")
    while offset < len(payload):
        chunk_size = int.from_bytes(payload[offset:offset + 4], byteorder="big")
        chunk_type = payload[offset + 4:offset + 8]
        if chunk_type == b"IEND":
            exif = b"Exif\x00\x00"
            chunk = (
                len(exif).to_bytes(4, byteorder="big")
                + b"eXIf"
                + exif
                + zlib.crc32(b"eXIf" + exif).to_bytes(4, byteorder="big")
            )
            return payload[:offset] + chunk + payload[offset:]
        offset += 12 + chunk_size
    raise AssertionError("PNG fixture has no IEND chunk")


def animated_png_bytes() -> bytes:
    first = Image.new("RGB", (8, 6), color=(22, 163, 183))
    second = Image.new("RGB", (8, 6), color=(12, 74, 110))
    stream = BytesIO()
    try:
        first.save(stream, format="PNG", save_all=True, append_images=[second], duration=100, loop=0)
        return stream.getvalue()
    finally:
        first.close()
        second.close()


def oversized_dimension_png_bytes() -> bytes:
    image = Image.new("RGB", (8_193, 1), color=(22, 163, 183))
    stream = BytesIO()
    try:
        image.save(stream, format="PNG")
        return stream.getvalue()
    finally:
        image.close()


def structurally_truncated_rgb_png_bytes() -> bytes:
    """A CRC-valid PNG whose decompressed scanline lacks one RGB pixel."""

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            len(payload).to_bytes(4, byteorder="big")
            + kind
            + payload
            + zlib.crc32(kind + payload).to_bytes(4, byteorder="big")
        )

    header = struct.pack(
        ">IIBBBBB",
        2,
        1,
        8,
        2,
        0,
        0,
        0,
    )
    # RGB 2×1 needs one filter byte plus six pixel bytes. This has only three
    # pixel bytes but carries a valid compressed stream and CRCs.
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\x00\x16\xa3\xb7"))
        + chunk(b"IEND", b"")
    )


def seed_completed_operation(
    db,
    *,
    operation_id: str,
    kind: str,
    extension: str,
    content_type: str,
    payload: bytes,
    source_page_count: int = 1,
    output_page_count: int | None = None,
    original_filename: str | None = None,
    selected_start_page: int | None = None,
    selected_end_page: int | None = None,
) -> Path:
    root = db.document_operations_directory()
    storage_key = f"outputs/{operation_id.replace('-', '')}.{extension.removeprefix('.')}"
    output = root / storage_key
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache,
                is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, NULL, 'user', 1, 1, ?, ?)""",
            (ACCOUNT_ID, "document-export-source@example.com", "not-a-login-hash", "Export Source", now, now),
        )
        conn.execute(
            """INSERT OR IGNORE INTO web_asset_files
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
               VALUES (?, ?, ?, NULL, ?, 'completed', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL,
                       ?, ?, ?, ?, ?)""",
            (
                operation_id,
                ACCOUNT_ID,
                SOURCE_ASSET_ID,
                kind,
                f"document-export-{operation_id}",
                "b" * 64,
                "c" * 64,
                1,
                "",
                selected_start_page,
                selected_end_page,
                source_page_count,
                output_page_count,
                storage_key,
                original_filename or REAL_OUTPUT_FILENAMES[kind],
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
    assert output.is_file()
    return output


def operation_state(tmp_path: Path, operation_id: str) -> str:
    with sqlite3.connect(tmp_path / "document-operation-export-docx-txt.db") as conn:
        row = conn.execute("SELECT state FROM web_document_operations WHERE id=?", (operation_id,)).fetchone()
    assert row is not None
    return str(row[0])


def test_completed_docx_and_utf8_text_sources_are_accepted_with_canonical_metadata(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    docx_operation_id = "30000000-0000-4000-8000-000000000001"
    text_operation_id = "30000000-0000-4000-8000-000000000002"
    docx_payload = valid_docx_bytes()
    text_payload = "Kết quả OCR UTF-8 hợp lệ.\n".encode("utf-8")
    seed_completed_operation(
        db,
        operation_id=docx_operation_id,
        kind="pdf_to_word_text",
        extension=".docx",
        content_type=DOCX_MEDIA_TYPE,
        payload=docx_payload,
    )
    seed_completed_operation(
        db,
        operation_id=text_operation_id,
        kind="image_ocr",
        extension=".txt",
        content_type=UTF8_TEXT_MEDIA_TYPE,
        payload=text_payload,
    )

    docx_result = operations.open_document_operation_export_source(
        operation_id=docx_operation_id,
        account_id=ACCOUNT_ID,
    )
    assert docx_result.failure is None
    assert docx_result.source is not None
    try:
        assert docx_result.source.kind == "pdf_to_word_text"
        assert docx_result.source.original_filename == "toan-aas-pdf-text.docx"
        assert docx_result.source.extension == ".docx"
        assert docx_result.source.content_type == DOCX_MEDIA_TYPE
        assert docx_result.source.byte_size == len(docx_payload)
        assert docx_result.source.stream.read() == docx_payload
    finally:
        docx_result.close()

    text_result = operations.open_document_operation_export_source(
        operation_id=text_operation_id,
        account_id=ACCOUNT_ID,
    )
    assert text_result.failure is None
    assert text_result.source is not None
    try:
        assert text_result.source.kind == "image_ocr"
        assert text_result.source.original_filename == "toan-aas-image-ocr.txt"
        assert text_result.source.extension == ".txt"
        assert text_result.source.content_type == UTF8_TEXT_MEDIA_TYPE
        assert text_result.source.byte_size == len(text_payload)
        assert text_result.source.stream.read() == text_payload
    finally:
        text_result.close()


@pytest.mark.parametrize(
    ("kind", "original_filename"),
    (
        ("pdf_merge", "toan-aas-merged-pdf.pdf"),
        ("pdf_optimize", "toan-aas-optimized-pdf.pdf"),
        ("image_to_pdf", "toan-aas-images.pdf"),
    ),
)
def test_pdf_export_source_uses_the_exact_writer_filename(tmp_path, monkeypatch, kind: str, original_filename: str) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    operation_id = "30000000-0000-4000-8000-000000000016"
    payload = valid_pdf_bytes()
    seed_completed_operation(
        db,
        operation_id=operation_id,
        kind=kind,
        extension=".pdf",
        content_type="application/pdf",
        payload=payload,
        output_page_count=1,
        original_filename=original_filename,
    )

    result = operations.open_document_operation_export_source(operation_id=operation_id, account_id=ACCOUNT_ID)

    assert result.failure is None
    assert result.source is not None
    try:
        assert result.source.original_filename == original_filename
    finally:
        result.close()


@pytest.mark.parametrize("unsafe_case", ("macro", "external", "traversal"))
def test_unsafe_docx_source_is_typed_integrity_failure_without_lifecycle_mutation(tmp_path, monkeypatch, unsafe_case: str) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    operation_id = "30000000-0000-4000-8000-000000000010"
    seed_completed_operation(
        db,
        operation_id=operation_id,
        kind="pdf_to_word_text",
        extension=".docx",
        content_type=DOCX_MEDIA_TYPE,
        payload=unsafe_docx_bytes(unsafe_case),
    )

    result = operations.open_document_operation_export_source(operation_id=operation_id, account_id=ACCOUNT_ID)

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.SOURCE_INTEGRITY
    assert result.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_SOURCE_UNAVAILABLE"
    assert operation_state(tmp_path, operation_id) == "completed"


def test_non_utf8_text_source_is_typed_integrity_failure_without_lifecycle_mutation(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    operation_id = "30000000-0000-4000-8000-000000000011"
    seed_completed_operation(
        db,
        operation_id=operation_id,
        kind="image_ocr",
        extension=".txt",
        content_type=UTF8_TEXT_MEDIA_TYPE,
        payload=b"\xff\xfebroken-utf8",
    )

    result = operations.open_document_operation_export_source(operation_id=operation_id, account_id=ACCOUNT_ID)

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.SOURCE_INTEGRITY
    assert result.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_SOURCE_UNAVAILABLE"
    assert operation_state(tmp_path, operation_id) == "completed"


def test_changed_operation_filename_is_typed_source_integrity_before_a_stream_is_returned(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    operation_id = "30000000-0000-4000-8000-000000000013"
    seed_completed_operation(
        db,
        operation_id=operation_id,
        kind="pdf_to_word_text",
        extension=".docx",
        content_type=DOCX_MEDIA_TYPE,
        payload=valid_docx_bytes(),
        original_filename="renamed-output.docx",
    )

    result = operations.open_document_operation_export_source(operation_id=operation_id, account_id=ACCOUNT_ID)

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.SOURCE_INTEGRITY
    assert operation_state(tmp_path, operation_id) == "completed"


@pytest.mark.parametrize(
    "payload",
    (
        rewritten_docx_bytes(omit=frozenset({"_rels/.rels"})),
        rewritten_docx_bytes(
            replacements={
                "word/document.xml": (
                    b"<?xml version='1.0' encoding='UTF-8'?>"
                    b"<!DOCTYPE w:document [<!ENTITY unsafe 'value'>]>"
                    b"<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
                    b"<w:body><w:p><w:r><w:t>&unsafe;</w:t></w:r></w:p></w:body></w:document>"
                ),
            },
        ),
        rewritten_docx_bytes(
            replacements={
                "word/document.xml": (
                    "<?xml version='1.0' encoding='UTF-16'?>"
                    "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'/>"
                ).encode("utf-16"),
            },
        ),
        underreported_eocd_docx_bytes(),
    ),
    ids=("missing-root-relationships", "dtd-entity", "utf16-required-xml", "eocd-count-mismatch"),
)
def test_malicious_opc_docx_is_rejected_as_source_integrity(tmp_path, monkeypatch, payload: bytes) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    operation_id = "30000000-0000-4000-8000-000000000014"
    seed_completed_operation(
        db,
        operation_id=operation_id,
        kind="pdf_to_word_text",
        extension=".docx",
        content_type=DOCX_MEDIA_TYPE,
        payload=payload,
    )

    result = operations.open_document_operation_export_source(operation_id=operation_id, account_id=ACCOUNT_ID)

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.SOURCE_INTEGRITY
    assert operation_state(tmp_path, operation_id) == "completed"


@pytest.mark.parametrize("payload", (b" \t\r\n", b"valid prefix\x00hidden suffix"), ids=("whitespace", "nul"))
def test_text_without_visible_nul_free_content_is_rejected_as_source_integrity(
    tmp_path,
    monkeypatch,
    payload: bytes,
) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    operation_id = "30000000-0000-4000-8000-000000000015"
    seed_completed_operation(
        db,
        operation_id=operation_id,
        kind="image_ocr",
        extension=".txt",
        content_type=UTF8_TEXT_MEDIA_TYPE,
        payload=payload,
    )

    result = operations.open_document_operation_export_source(operation_id=operation_id, account_id=ACCOUNT_ID)

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.SOURCE_INTEGRITY
    assert operation_state(tmp_path, operation_id) == "completed"


def test_multi_page_pdf_to_images_zip_remains_ineligible_even_with_a_real_output_file(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    operation_id = "30000000-0000-4000-8000-000000000012"
    seed_completed_operation(
        db,
        operation_id=operation_id,
        kind="pdf_to_images",
        extension=".zip",
        content_type="application/zip",
        payload=real_zip_bytes(),
        output_page_count=2,
    )

    result = operations.open_document_operation_export_source(operation_id=operation_id, account_id=ACCOUNT_ID)

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.PRECONDITION
    assert result.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_NOT_ELIGIBLE"
    assert operations.mark_document_operation_export_source_unavailable(result) is False
    assert operation_state(tmp_path, operation_id) == "completed"


def test_pdf_to_images_requires_matching_single_source_and_output_page_counts(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    operation_id = "30000000-0000-4000-8000-000000000016"
    seed_completed_operation(
        db,
        operation_id=operation_id,
        kind="pdf_to_images",
        extension=".png",
        content_type="image/png",
        payload=real_png_bytes(),
        source_page_count=2,
        output_page_count=1,
        original_filename="toan-aas-pdf-page-001.png",
    )

    result = operations.open_document_operation_export_source(
        operation_id=operation_id,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.PRECONDITION
    assert result.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_NOT_ELIGIBLE"
    assert operations.mark_document_operation_export_source_unavailable(result) is False
    assert operation_state(tmp_path, operation_id) == "completed"


@pytest.mark.parametrize(
    ("content_type", "original_filename"),
    (
        ("image/jpeg", "toan-aas-pdf-page-001.png"),
        ("image/png", "renamed-page.png"),
    ),
)
def test_pdf_to_images_requires_the_canonical_png_descriptor(
    tmp_path,
    monkeypatch,
    content_type: str,
    original_filename: str,
) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    operation_id = "30000000-0000-4000-8000-000000000017"
    seed_completed_operation(
        db,
        operation_id=operation_id,
        kind="pdf_to_images",
        extension=".png",
        content_type=content_type,
        payload=real_png_bytes(),
        output_page_count=1,
        original_filename=original_filename,
    )

    result = operations.open_document_operation_export_source(
        operation_id=operation_id,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.SOURCE_INTEGRITY
    assert result.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_SOURCE_UNAVAILABLE"
    assert operations.mark_document_operation_export_source_unavailable(result) is True
    assert operation_state(tmp_path, operation_id) == "unavailable"


@pytest.mark.parametrize(
    ("suffix", "payload"),
    (
        ("magic", b"not-a-png"),
        ("exif", png_with_exif_chunk()),
        ("apng", animated_png_bytes()),
        ("dimension", oversized_dimension_png_bytes()),
    ),
)
def test_single_page_pdf_to_images_rejects_unsafe_png_source(tmp_path, monkeypatch, suffix: str, payload: bytes) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    operation_id = f"30000000-0000-4000-8000-0000000000{20 + len(suffix):02d}"
    seed_completed_operation(
        db,
        operation_id=operation_id,
        kind="pdf_to_images",
        extension=".png",
        content_type="image/png",
        payload=payload,
        output_page_count=1,
        original_filename="toan-aas-pdf-page-001.png",
    )

    result = operations.open_document_operation_export_source(
        operation_id=operation_id,
        account_id=ACCOUNT_ID,
    )

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.SOURCE_INTEGRITY
    assert result.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_SOURCE_UNAVAILABLE"
    assert operations.mark_document_operation_export_source_unavailable(result) is True
    assert operation_state(tmp_path, operation_id) == "unavailable"


def test_pdf_to_images_retries_when_pillow_global_allows_truncation(tmp_path, monkeypatch) -> None:
    db, operations = load_modules(tmp_path, monkeypatch)
    operation_id = "30000000-0000-4000-8000-000000000030"
    seed_completed_operation(
        db,
        operation_id=operation_id,
        kind="pdf_to_images",
        extension=".png",
        content_type="image/png",
        payload=structurally_truncated_rgb_png_bytes(),
        output_page_count=1,
        original_filename="toan-aas-pdf-page-001.png",
    )
    original = ImageFile.LOAD_TRUNCATED_IMAGES
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    try:
        result = operations.open_document_operation_export_source(
            operation_id=operation_id,
            account_id=ACCOUNT_ID,
        )
    finally:
        ImageFile.LOAD_TRUNCATED_IMAGES = original

    assert result.source is None
    assert result.failure is not None
    assert result.failure.domain is operations.DocumentOperationExportFailureDomain.DESTINATION
    assert result.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_BUSY"
    assert operations.mark_document_operation_export_source_unavailable(result) is False
    assert operation_state(tmp_path, operation_id) == "completed"

    retry = operations.open_document_operation_export_source(
        operation_id=operation_id,
        account_id=ACCOUNT_ID,
    )

    assert retry.source is None
    assert retry.failure is not None
    assert retry.failure.domain is operations.DocumentOperationExportFailureDomain.SOURCE_INTEGRITY
    assert retry.failure.code == "WEB_DOCUMENT_OPERATION_EXPORT_SOURCE_UNAVAILABLE"
    assert operations.mark_document_operation_export_source_unavailable(retry) is True
    assert operation_state(tmp_path, operation_id) == "unavailable"
