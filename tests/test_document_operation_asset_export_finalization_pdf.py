"""TDD contracts for Document Operation Asset Vault finalization."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta
from io import BytesIO
import hashlib
import importlib
import os
from pathlib import Path
import sqlite3
import stat
import struct
import sys
import time
import warnings
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from fastapi import HTTPException
import pytest
from pypdf import PdfWriter


ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"
SOURCE_ASSET_ID = "22222222-2222-4222-8222-222222222222"
OPERATION_ID = "33333333-3333-4333-8333-333333333333"
DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
CONTENT_TYPES_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/content-types"
RELATIONSHIPS_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_DOCUMENT_RELATIONSHIP = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
)
WORD_MAIN_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)
DOCUMENT_EXPORT_SPECS = {
    "pdf_split": (".pdf", "application/pdf", "toan-aas-pdf-split.pdf"),
    "pdf_merge": (".pdf", "application/pdf", "toan-aas-pdf-merged.pdf"),
    "pdf_optimize": (".pdf", "application/pdf", "toan-aas-pdf-optimized.pdf"),
    "image_to_pdf": (".pdf", "application/pdf", "toan-aas-images.pdf"),
    "pdf_to_word_text": (".docx", DOCX_CONTENT_TYPE, "toan-aas-pdf-text.docx"),
    "pdf_ocr_word": (".docx", DOCX_CONTENT_TYPE, "toan-aas-pdf-ocr.docx"),
    "image_ocr": (".txt", "text/plain; charset=utf-8", "toan-aas-image-ocr.txt"),
    "pdf_ocr": (".txt", "text/plain; charset=utf-8", "toan-aas-pdf-ocr.txt"),
}
REAL_OUTPUT_FILENAMES = {
    "pdf_split": "toan-aas-pdf-pages-1-2.pdf",
    "pdf_to_images": "toan-aas-pdf-pages.zip",
    "pdf_merge": "toan-aas-merged-pdf.pdf",
    "pdf_optimize": "toan-aas-optimized-pdf.pdf",
    "image_to_pdf": "toan-aas-images.pdf",
    "pdf_to_word_text": "toan-aas-pdf-text.docx",
    "pdf_ocr_word": "toan-aas-pdf-ocr.docx",
    "image_ocr": "toan-aas-image-ocr.txt",
    "pdf_ocr": "toan-aas-pdf-ocr.txt",
}


class CloseValueErrorStream(BytesIO):
    """Model a stream that closes successfully and then reports ValueError."""

    def close(self) -> None:
        super().close()
        raise ValueError("synthetic close failure")


def load_modules(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WEBAPP_SESSION_DB_PATH", str(tmp_path / "document-export-finalization-pdf.db"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_ROOT", str(tmp_path / "private-web-assets"))
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "20")
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "100")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATIONS_ENABLED", "true")
    monkeypatch.setenv("WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED", "true")
    for name in ("copyfast_db", "copyfast_auth", "copyfast_assets"):
        sys.modules.pop(name, None)
    db = importlib.import_module("copyfast_db")
    assets = importlib.import_module("copyfast_assets")
    db.ensure_copyfast_schema()
    return db, assets


def pdf_bytes(page_count: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=144, height=144)
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def docx_bytes(
    *,
    include_macro: bool = False,
    include_external_relationship: bool = False,
    include_traversal: bool = False,
    include_symlink: bool = False,
    include_duplicate: bool = False,
    include_embedding: bool = False,
    include_activex: bool = False,
    include_content_types: bool = True,
    include_package_relationships: bool = True,
    include_document: bool = True,
    extra_members: int = 0,
    content_types_payload: bytes | None = None,
    package_relationships_payload: bytes | None = None,
    document_payload: bytes | None = None,
) -> bytes:
    """Build the smallest safe OOXML fixture, with opt-in hostile members."""

    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED) as archive:
        if include_content_types:
            archive.writestr(
                "[Content_Types].xml",
                content_types_payload
                or (
                    f"<?xml version='1.0'?><Types xmlns='{CONTENT_TYPES_NAMESPACE}'>"
                    f"<Override PartName='/word/document.xml' ContentType='{WORD_MAIN_CONTENT_TYPE}' />"
                    "</Types>"
                ).encode("utf-8"),
            )
        if include_package_relationships:
            archive.writestr(
                "_rels/.rels",
                package_relationships_payload
                or (
                    f"<?xml version='1.0'?><Relationships xmlns='{RELATIONSHIPS_NAMESPACE}'>"
                    f"<Relationship Id='rId1' Type='{OFFICE_DOCUMENT_RELATIONSHIP}' "
                    "Target='word/document.xml' />"
                    "</Relationships>"
                ).encode("utf-8"),
            )
        if include_document:
            archive.writestr(
                "word/document.xml",
                document_payload
                or b"<?xml version='1.0'?><w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p /></w:body></w:document>",
            )
        if include_duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr("word/document.xml", b"duplicate document part must be rejected")
        if include_macro:
            archive.writestr("word/vbaProject.bin", b"not-a-macro-but-must-be-rejected")
        if include_external_relationship:
            archive.writestr(
                "word/_rels/document.xml.rels",
                (
                    f"<Relationships xmlns='{RELATIONSHIPS_NAMESPACE}'>"
                    "<Relationship Id='rIdExternal' Type='urn:external-test' "
                    "Target='https://example.invalid' TargetMode='External' />"
                    "</Relationships>"
                ).encode("utf-8"),
            )
        if include_traversal:
            archive.writestr("../outside.xml", b"must-not-be-accepted")
        if include_symlink:
            link = ZipInfo("word/media/link.bin")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(link, b"target")
        if include_embedding:
            archive.writestr("word/embeddings/oleObject1.bin", b"embedded object")
        if include_activex:
            archive.writestr("word/activeX/activeX1.bin", b"ActiveX control")
        for index in range(extra_members):
            archive.writestr(f"word/customXml/item-{index}.xml", b"<item />")
    return stream.getvalue()


def crc_corrupted_docx_bytes() -> bytes:
    """Return a structurally DOCX-looking archive with a bad member CRC."""

    payload = bytearray(docx_bytes())
    with ZipFile(BytesIO(payload), "r") as archive:
        info = archive.getinfo("word/document.xml")
    central_header = payload.rindex(b"PK\x01\x02")
    # ZipFile validates a member against the central-directory CRC.  Altering
    # that field produces a deterministic CRC failure; changing an arbitrary
    # deflate byte can instead land in unused compressed padding and remain a
    # valid member on some Python/zlib versions.
    central_crc = struct.unpack_from("<I", payload, central_header + 16)[0]
    assert central_crc == info.CRC
    struct.pack_into("<I", payload, central_header + 16, central_crc ^ 0x01)
    return bytes(payload)


def encrypted_docx_bytes() -> bytes:
    """Mark the ZIP members encrypted without relying on a non-stdlib writer."""

    payload = bytearray(docx_bytes())
    local_header = payload.index(b"PK\x03\x04")
    central_header = payload.index(b"PK\x01\x02")
    local_flags = struct.unpack_from("<H", payload, local_header + 6)[0]
    central_flags = struct.unpack_from("<H", payload, central_header + 8)[0]
    struct.pack_into("<H", payload, local_header + 6, local_flags | 0x1)
    struct.pack_into("<H", payload, central_header + 8, central_flags | 0x1)
    return bytes(payload)


def docx_with_eocd_entry_count(entry_count: int) -> bytes:
    """Mutate only classic EOCD counts, leaving a small physical archive."""

    payload = bytearray(docx_bytes())
    eocd = payload.rfind(b"PK\x05\x06")
    assert eocd >= 0
    struct.pack_into("<H", payload, eocd + 8, entry_count)
    struct.pack_into("<H", payload, eocd + 10, entry_count)
    return bytes(payload)


def docx_with_underreported_eocd_entry_count(max_members: int) -> bytes:
    """Keep too many physical central-directory entries but declare only one."""

    payload = bytearray(docx_bytes(extra_members=max_members - 2))
    eocd = payload.rfind(b"PK\x05\x06")
    assert eocd >= 0
    struct.pack_into("<H", payload, eocd + 8, 1)
    struct.pack_into("<H", payload, eocd + 10, 1)
    return bytes(payload)


def docx_with_eocd_field(*, offset: int, format_code: str, value: int) -> bytes:
    payload = bytearray(docx_bytes())
    eocd = payload.rfind(b"PK\x05\x06")
    assert eocd >= 0
    struct.pack_into("<" + format_code, payload, eocd + offset, value)
    return bytes(payload)


def seed_completed_document_operation(
    db,
    *,
    payload: bytes,
    kind: str = "pdf_split",
) -> None:
    digest = hashlib.sha256(payload).hexdigest()
    extension, content_type, _canonical_filename = DOCUMENT_EXPORT_SPECS.get(
        kind,
        (".zip", "application/zip", REAL_OUTPUT_FILENAMES["pdf_to_images"]),
    )
    original_filename = REAL_OUTPUT_FILENAMES.get(kind, REAL_OUTPUT_FILENAMES["pdf_to_images"])
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_accounts
               (id, email, password_hash, display_name, canonical_user_id, role_cache,
                is_active, password_login_enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, NULL, 'user', 1, 1, ?, ?)""",
            (ACCOUNT_ID, "document-export-finalization@example.com", "not-a-login-hash", "PDF Export", now, now),
        )
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension,
                content_type, byte_size, sha256, storage_key, state, lifecycle_revision,
                created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, '.pdf', 'application/pdf', ?, ?, ?, 'active', 1, ?, ?, NULL)""",
            (
                SOURCE_ASSET_ID,
                ACCOUNT_ID,
                "Nguồn PDF",
                "source.pdf",
                len(payload),
                digest,
                "objects/" + "1" * 32 + ".blob",
                now,
                now,
            ),
        )
        conn.execute(
            """INSERT INTO web_document_operations
               (id, account_id, source_asset_id, project_id, kind, state, idempotency_key,
                request_fingerprint, source_sha256, source_byte_size, source_count,
                requested_page_range, selected_start_page, selected_end_page, source_page_count,
                output_page_count, storage_key, original_filename, content_type, byte_size,
                sha256, failure_code, created_at, queued_at, started_at, completed_at, updated_at)
                VALUES (?, ?, ?, NULL, ?, 'completed', ?, ?, ?, ?, 1,
                        '1-2', 1, 2, 2, 2, ?, ?, ?, ?,
                       ?, NULL, ?, ?, ?, ?, ?)""",
            (
                OPERATION_ID,
                ACCOUNT_ID,
                SOURCE_ASSET_ID,
                kind,
                "document-finalization-seed-0001",
                digest,
                digest,
                len(payload),
                "outputs/" + "2" * 32 + extension,
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


def reserve(assets, payload: bytes, *, key: str):
    return assets.reserve_document_operation_asset_export(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        idempotency_key=key,
        request_fingerprint=hashlib.sha256(payload).hexdigest(),
        expected_bytes=len(payload),
    )


def pdf_source(
    assets,
    payload: bytes,
    *,
    kind: str = "pdf_split",
    extension: str = ".pdf",
    content_type: str = "application/pdf",
):
    expected = DOCUMENT_EXPORT_SPECS.get(kind)
    original_filename = expected[2] if expected and (extension, content_type) == expected[:2] else "toan-aas-invalid" + extension
    return assets.DocumentOperationAssetExportSource(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        kind=kind,
        project_id=None,
        original_filename=original_filename,
        extension=extension,
        content_type=content_type,
        byte_size=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        stream=BytesIO(payload),
    )


def document_source(assets, payload: bytes, *, kind: str):
    extension, content_type, original_filename = DOCUMENT_EXPORT_SPECS[kind]
    return assets.DocumentOperationAssetExportSource(
        account_id=ACCOUNT_ID,
        operation_id=OPERATION_ID,
        kind=kind,
        project_id=None,
        original_filename=original_filename,
        extension=extension,
        content_type=content_type,
        byte_size=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        stream=BytesIO(payload),
    )


def assert_no_document_export_artifacts(tmp_path: Path) -> None:
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        copied_asset_count = conn.execute(
            "SELECT COUNT(*) FROM web_asset_files WHERE id != ?",
            (SOURCE_ASSET_ID,),
        ).fetchone()[0]
        audit_count = conn.execute(
            "SELECT COUNT(*) FROM web_audit_events WHERE action='web.document_operation.export_to_asset_vault'"
        ).fetchone()[0]
    assert copied_asset_count == 0
    assert audit_count == 0
    assert not list((tmp_path / "private-web-assets" / "objects").glob("*.blob"))
    assert not list((tmp_path / "private-web-assets" / ".staging").glob("*"))


def assert_document_export_remains_copying(tmp_path: Path) -> None:
    assert_no_document_export_artifacts(tmp_path)
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        relation_state = conn.execute(
            "SELECT state FROM web_document_operation_asset_exports WHERE operation_id=?",
            (OPERATION_ID,),
        ).fetchone()[0]
    assert relation_state == "copying"


@pytest.mark.parametrize("kind", ("pdf_split", "pdf_merge", "pdf_optimize", "image_to_pdf"))
def test_finalizing_current_pdf_lease_creates_one_private_asset(tmp_path, monkeypatch, kind: str) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    seed_completed_document_operation(db, payload=payload, kind=kind)
    reservation = reserve(assets, payload, key="document-finalization-pdf-0001")
    assert reservation.lease is not None

    finalize = assets.finalize_document_operation_asset_export
    source = pdf_source(assets, payload, kind=kind)
    finalized = finalize(
        lease=reservation.lease,
        source=source,
        request_id="document-finalization-pdf-request",
    )

    assert source.stream.closed is True
    assert finalized.state == "completed"
    assert finalized.asset is not None
    assert finalized.asset["original_filename"] == DOCUMENT_EXPORT_SPECS[kind][2]
    assert finalized.asset["extension"] == ".pdf"
    assert finalized.asset["content_type"] == "application/pdf"
    assert finalized.asset["byte_size"] == len(payload)
    assert set(finalized.asset) == {
        "id",
        "project_id",
        "display_name",
        "original_filename",
        "extension",
        "content_type",
        "byte_size",
        "state",
        "created_at",
        "updated_at",
        "archived_at",
    }
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        relation = conn.execute(
            """SELECT asset_id, state, lease_token, reserved_bytes, pending_storage_key
               FROM web_document_operation_asset_exports WHERE operation_id=?""",
            (OPERATION_ID,),
        ).fetchone()
        asset = conn.execute(
            """SELECT account_id, original_filename, extension, content_type, byte_size, sha256,
                      storage_key, state
               FROM web_asset_files WHERE id=?""",
            (finalized.asset["id"],),
        ).fetchone()
        raw_output_filename = conn.execute(
            "SELECT original_filename FROM web_document_operations WHERE id=?",
            (OPERATION_ID,),
        ).fetchone()[0]
        audit = conn.execute(
            "SELECT action, target FROM web_audit_events WHERE target=?",
            (finalized.asset["id"],),
        ).fetchone()
    assert relation == (finalized.asset["id"], "completed", None, 0, None)
    assert raw_output_filename == REAL_OUTPUT_FILENAMES[kind]
    assert asset[:6] == (
        ACCOUNT_ID,
        DOCUMENT_EXPORT_SPECS[kind][2],
        ".pdf",
        "application/pdf",
        len(payload),
        digest,
    )
    assert asset[7] == "active"
    assert audit == ("web.document_operation.export_to_asset_vault", finalized.asset["id"])
    copied = tmp_path / "private-web-assets" / asset[6]
    assert copied.read_bytes() == payload
    assert not list((tmp_path / "private-web-assets" / ".staging").glob("*"))


@pytest.mark.parametrize(
    ("kind", "payload"),
    (
        ("pdf_to_word_text", docx_bytes()),
        ("pdf_ocr_word", docx_bytes()),
        ("image_ocr", "Nội dung OCR đã xác minh.\n".encode("utf-8")),
        ("pdf_ocr", "Nội dung OCR PDF đã xác minh.\n".encode("utf-8")),
    ),
)
def test_finalizing_current_docx_or_text_lease_creates_one_private_asset(
    tmp_path,
    monkeypatch,
    kind: str,
    payload: bytes,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    extension, content_type, expected_filename = DOCUMENT_EXPORT_SPECS[kind]
    seed_completed_document_operation(db, payload=payload, kind=kind)
    reservation = reserve(assets, payload, key=f"document-finalization-{kind}-accept-0001")
    assert reservation.lease is not None
    source = document_source(assets, payload, kind=kind)

    finalized = assets.finalize_document_operation_asset_export(
        lease=reservation.lease,
        source=source,
        request_id=f"document-finalization-{kind}-accept-request",
    )

    assert source.stream.closed is True
    assert finalized.state == "completed"
    assert finalized.asset is not None
    assert finalized.asset["original_filename"] == expected_filename
    assert finalized.asset["extension"] == extension
    assert finalized.asset["content_type"] == content_type
    assert finalized.asset["byte_size"] == len(payload)
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        asset = conn.execute(
            """SELECT original_filename, extension, content_type, storage_key, state
               FROM web_asset_files WHERE id=?""",
            (finalized.asset["id"],),
        ).fetchone()
        relation = conn.execute(
            "SELECT state, asset_id FROM web_document_operation_asset_exports WHERE operation_id=?",
            (OPERATION_ID,),
        ).fetchone()
    assert asset[:3] == (expected_filename, extension, content_type)
    assert asset[4] == "active"
    assert relation == ("completed", finalized.asset["id"])
    assert (tmp_path / "private-web-assets" / asset[3]).read_bytes() == payload


@pytest.mark.parametrize(
    "payload",
    (
        docx_bytes(include_macro=True),
        docx_bytes(include_external_relationship=True),
        docx_bytes(include_traversal=True),
        docx_bytes(include_symlink=True),
        docx_bytes(include_duplicate=True),
        encrypted_docx_bytes(),
        docx_bytes(include_embedding=True),
        docx_bytes(include_activex=True),
        docx_bytes(include_content_types=False),
        docx_bytes(include_package_relationships=False),
        docx_bytes(include_document=False),
        crc_corrupted_docx_bytes(),
    ),
    ids=(
        "macro",
        "external-relationship",
        "traversal",
        "symlink",
        "duplicate",
        "encrypted",
        "embedding",
        "activex",
        "missing-content-types",
        "missing-package-relationships",
        "missing-document",
        "crc",
    ),
)
def test_unsafe_docx_cannot_create_asset_or_leave_export_artifacts(tmp_path, monkeypatch, payload: bytes) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_document_operation(db, payload=payload, kind="pdf_to_word_text")
    reservation = reserve(assets, payload, key="document-finalization-docx-unsafe-0001")
    assert reservation.lease is not None
    source = document_source(assets, payload, kind="pdf_to_word_text")

    with pytest.raises(RuntimeError):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-docx-unsafe-request",
        )

    assert source.stream.closed is True
    assert_no_document_export_artifacts(tmp_path)


@pytest.mark.parametrize(
    "payload",
    (
        docx_bytes(
            package_relationships_payload=(
                f"<Relationships xmlns='{RELATIONSHIPS_NAMESPACE}'>"
                f"<Relationship Id='rId1' Type='{OFFICE_DOCUMENT_RELATIONSHIP}' "
                "Target='word/other.xml' />"
                "</Relationships>"
            ).encode("utf-8"),
        ),
        docx_bytes(
            package_relationships_payload=(
                f"<Relationships xmlns='{RELATIONSHIPS_NAMESPACE}'>"
                "<Relationship Id='rId1' Type='urn:not-office-document' "
                "Target='word/document.xml' />"
                "</Relationships>"
            ).encode("utf-8"),
        ),
        docx_bytes(
            package_relationships_payload=(
                f"<Relationships xmlns='{RELATIONSHIPS_NAMESPACE}'>"
                f"<Relationship Type='{OFFICE_DOCUMENT_RELATIONSHIP}' "
                "Target='word/document.xml' />"
                "</Relationships>"
            ).encode("utf-8"),
        ),
        docx_bytes(
            package_relationships_payload=(
                f"<Relationships xmlns='{RELATIONSHIPS_NAMESPACE}'>"
                f"<Relationship Id='rId1' Type='{OFFICE_DOCUMENT_RELATIONSHIP}' "
                "Target='word/document.xml' />"
                "<Relationship Id='rId1' Type='urn:duplicate-id' Target='word/other.xml' />"
                "</Relationships>"
            ).encode("utf-8"),
        ),
        docx_bytes(
            package_relationships_payload=(
                f"<Relationships xmlns='{RELATIONSHIPS_NAMESPACE}'>"
                f"<Relationship Id='r Id1' Type='{OFFICE_DOCUMENT_RELATIONSHIP}' "
                "Target='word/document.xml' />"
                "</Relationships>"
            ).encode("utf-8"),
        ),
        docx_bytes(
            package_relationships_payload=(
                f"<Relationships xmlns='{RELATIONSHIPS_NAMESPACE}'>"
                f"<Relationship Id='r&#x85;Id1' Type='{OFFICE_DOCUMENT_RELATIONSHIP}' "
                "Target='word/document.xml' />"
                "</Relationships>"
            ).encode("utf-8"),
        ),
        docx_bytes(
            package_relationships_payload=(
                f"<Relationships xmlns='{RELATIONSHIPS_NAMESPACE}'>"
                "<Wrapper>"
                f"<Relationship Id='rId1' Type='{OFFICE_DOCUMENT_RELATIONSHIP}' "
                "Target='word/document.xml' />"
                "</Wrapper>"
                "</Relationships>"
            ).encode("utf-8"),
        ),
        docx_bytes(
            content_types_payload=(
                f"<Types xmlns='{CONTENT_TYPES_NAMESPACE}'></Types>"
            ).encode("utf-8"),
        ),
        docx_bytes(
            content_types_payload=(
                f"<Types xmlns='{CONTENT_TYPES_NAMESPACE}'>"
                "<Override PartName='/word/document.xml' ContentType='application/xml' />"
                "</Types>"
            ).encode("utf-8"),
        ),
    ),
    ids=(
        "package-relationship-wrong-target",
        "package-relationship-wrong-type",
        "package-relationship-missing-id",
        "package-relationship-duplicate-id",
        "package-relationship-whitespace-id",
        "package-relationship-control-id",
        "package-relationship-nested",
        "missing-document-override",
        "invalid-document-override",
    ),
)
def test_non_opc_docx_cannot_create_asset_or_leave_export_artifacts(
    tmp_path,
    monkeypatch,
    payload: bytes,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_document_operation(db, payload=payload, kind="pdf_to_word_text")
    reservation = reserve(assets, payload, key="document-finalization-docx-non-opc-0001")
    assert reservation.lease is not None
    source = document_source(assets, payload, kind="pdf_to_word_text")

    with pytest.raises(RuntimeError):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-docx-non-opc-request",
        )

    assert source.stream.closed is True
    assert_no_document_export_artifacts(tmp_path)


@pytest.mark.parametrize(
    "payload",
    (
        docx_bytes(content_types_payload=b"<Types"),
        docx_bytes(document_payload=b"<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"),
    ),
    ids=("malformed-content-types", "malformed-document"),
)
def test_malformed_required_docx_xml_cannot_create_asset_or_leave_export_artifacts(
    tmp_path,
    monkeypatch,
    payload: bytes,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_document_operation(db, payload=payload, kind="pdf_to_word_text")
    reservation = reserve(assets, payload, key="document-finalization-docx-malformed-xml-0001")
    assert reservation.lease is not None
    source = document_source(assets, payload, kind="pdf_to_word_text")

    with pytest.raises(RuntimeError):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-docx-malformed-xml-request",
        )

    assert source.stream.closed is True
    assert_no_document_export_artifacts(tmp_path)


@pytest.mark.parametrize(
    "payload",
    (
        docx_bytes(
            content_types_payload=(
                b"<?xml version='1.0'?><!DOCTYPE Types [<!ENTITY harmless 'ok'>]>"
                b"<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types' />"
            )
        ),
        docx_bytes(
            document_payload=(
                b"<?xml version='1.0'?><!DOCTYPE w:document [<!ENTITY harmless 'ok'>]>"
                b"<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main' />"
            )
        ),
        docx_bytes(
            content_types_payload=(
                "<?xml version='1.0'?><!DOCTYPE Types [<!ENTITY harmless 'ok'>]>"
                f"<Types xmlns='{CONTENT_TYPES_NAMESPACE}'>"
                f"<Override PartName='/word/document.xml' ContentType='{WORD_MAIN_CONTENT_TYPE}' />"
                "</Types>"
            ).encode("utf-16")
        ),
    ),
    ids=("content-types-dtd-entity", "document-dtd-entity", "content-types-utf16-dtd-entity"),
)
def test_required_docx_xml_with_dtd_or_entity_cannot_create_asset_or_leave_export_artifacts(
    tmp_path,
    monkeypatch,
    payload: bytes,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_document_operation(db, payload=payload, kind="pdf_to_word_text")
    reservation = reserve(assets, payload, key="document-finalization-docx-dtd-entity-0001")
    assert reservation.lease is not None
    source = document_source(assets, payload, kind="pdf_to_word_text")

    with pytest.raises(RuntimeError):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-docx-dtd-entity-request",
        )

    assert source.stream.closed is True
    assert_no_document_export_artifacts(tmp_path)


@pytest.mark.parametrize(
    ("limit_name", "limit_value", "payload"),
    (
        ("DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_MEMBERS", 2, docx_bytes(extra_members=1)),
        ("DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_UNCOMPRESSED_BYTES", 128, docx_bytes()),
    ),
    ids=("member-bound", "uncompressed-bound"),
)
def test_bounded_docx_cannot_create_asset_or_leave_export_artifacts(
    tmp_path,
    monkeypatch,
    limit_name: str,
    limit_value: int,
    payload: bytes,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    monkeypatch.setattr(assets, limit_name, limit_value)
    seed_completed_document_operation(db, payload=payload, kind="pdf_to_word_text")
    reservation = reserve(assets, payload, key=f"document-finalization-docx-{limit_name}-0001")
    assert reservation.lease is not None
    source = document_source(assets, payload, kind="pdf_to_word_text")

    with pytest.raises(RuntimeError):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id=f"document-finalization-docx-{limit_name}-request",
        )

    assert source.stream.closed is True
    assert_no_document_export_artifacts(tmp_path)


def test_docx_eocd_member_count_is_rejected_before_zipfile_construction(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = docx_with_eocd_entry_count(
        assets.DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_MEMBERS + 1
    )
    seed_completed_document_operation(db, payload=payload, kind="pdf_to_word_text")
    reservation = reserve(assets, payload, key="document-finalization-docx-eocd-count-0001")
    assert reservation.lease is not None
    source = document_source(assets, payload, kind="pdf_to_word_text")

    def unexpected_zipfile_construction(*_args, **_kwargs):
        raise AssertionError("ZipFile must not be constructed for an oversized EOCD entry count")

    monkeypatch.setattr(assets, "ZipFile", unexpected_zipfile_construction)

    with pytest.raises(RuntimeError):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-docx-eocd-count-request",
        )

    assert source.stream.closed is True
    assert_no_document_export_artifacts(tmp_path)


def test_docx_underreported_eocd_member_count_is_rejected_before_zipfile_construction(
    tmp_path,
    monkeypatch,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = docx_with_underreported_eocd_entry_count(
        assets.DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_MEMBERS
    )
    seed_completed_document_operation(db, payload=payload, kind="pdf_to_word_text")
    reservation = reserve(assets, payload, key="document-finalization-docx-underreported-count-0001")
    assert reservation.lease is not None
    source = document_source(assets, payload, kind="pdf_to_word_text")

    def unexpected_zipfile_construction(*_args, **_kwargs):
        raise AssertionError("ZipFile must not be constructed for an underreported EOCD entry count")

    monkeypatch.setattr(assets, "ZipFile", unexpected_zipfile_construction)

    with pytest.raises(RuntimeError):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-docx-underreported-count-request",
        )

    assert source.stream.closed is True
    assert_no_document_export_artifacts(tmp_path)


@pytest.mark.parametrize(
    ("offset", "format_code", "value"),
    (
        (4, "H", 1),
        (10, "H", 0xFFFF),
        (12, "I", 1024 * 1024 + 1),
        (16, "I", 0),
    ),
    ids=("multi-disk", "zip64-sentinel", "central-directory-size", "central-directory-bounds"),
)
def test_invalid_classic_eocd_is_rejected_before_zipfile_construction(
    tmp_path,
    monkeypatch,
    offset: int,
    format_code: str,
    value: int,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = docx_with_eocd_field(offset=offset, format_code=format_code, value=value)
    seed_completed_document_operation(db, payload=payload, kind="pdf_to_word_text")
    reservation = reserve(assets, payload, key="document-finalization-docx-invalid-eocd-0001")
    assert reservation.lease is not None
    source = document_source(assets, payload, kind="pdf_to_word_text")

    def unexpected_zipfile_construction(*_args, **_kwargs):
        raise AssertionError("ZipFile must not be constructed for an invalid classic EOCD")

    monkeypatch.setattr(assets, "ZipFile", unexpected_zipfile_construction)

    with pytest.raises(RuntimeError):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-docx-invalid-eocd-request",
        )

    assert source.stream.closed is True
    assert_no_document_export_artifacts(tmp_path)


@pytest.mark.parametrize(
    "payload",
    (b" \t\n", b"valid\x00text", b"\xff\xfe"),
    ids=("whitespace", "nul", "non-utf8"),
)
def test_invalid_nonempty_text_cannot_create_asset_or_leave_export_artifacts(tmp_path, monkeypatch, payload: bytes) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    seed_completed_document_operation(db, payload=payload, kind="image_ocr")
    reservation = reserve(assets, payload, key="document-finalization-text-unsafe-0001")
    assert reservation.lease is not None
    source = document_source(assets, payload, kind="image_ocr")

    with pytest.raises(RuntimeError):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-text-unsafe-request",
        )

    assert source.stream.closed is True
    assert_no_document_export_artifacts(tmp_path)


def test_empty_text_stream_cannot_create_asset_or_leave_export_artifacts(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    # A current database lease can never reserve zero bytes.  Pin the lease to
    # an empty descriptor but retain its non-zero reservation to exercise the
    # finalizer's fail-closed copy boundary.
    reserved_payload = b"x"
    seed_completed_document_operation(db, payload=reserved_payload, kind="image_ocr")
    reservation = reserve(assets, reserved_payload, key="document-finalization-text-empty-0001")
    assert reservation.lease is not None
    source = document_source(assets, b"", kind="image_ocr")
    source = replace(source, byte_size=len(reserved_payload))
    lease = replace(reservation.lease, request_fingerprint=source.sha256)

    with pytest.raises(RuntimeError):
        assets.finalize_document_operation_asset_export(
            lease=lease,
            source=source,
            request_id="document-finalization-text-empty-request",
        )

    assert source.stream.closed is True
    assert_no_document_export_artifacts(tmp_path)


def test_invalid_pdf_cannot_create_an_asset_or_leave_a_private_blob(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = b"%PDF-1.7\nnot a complete PDF"
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key="document-finalization-invalid-pdf-0001")
    assert reservation.lease is not None
    source = pdf_source(assets, payload)

    with pytest.raises(RuntimeError, match="PDF"):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-invalid-pdf-request",
        )

    assert source.stream.closed is True
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        copied_asset_count = conn.execute(
            "SELECT COUNT(*) FROM web_asset_files WHERE id != ?",
            (SOURCE_ASSET_ID,),
        ).fetchone()[0]
        relation_state = conn.execute(
            "SELECT state FROM web_document_operation_asset_exports WHERE operation_id=?",
            (OPERATION_ID,),
        ).fetchone()[0]
    assert copied_asset_count == 0
    assert relation_state == "copying"
    assert not list((tmp_path / "private-web-assets" / "objects").glob("*.blob"))


def test_pdf_with_non_whitespace_after_eof_cannot_create_an_asset(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes() + b"\nTRAILER-GARBAGE"
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key="document-finalization-trailing-pdf-0001")
    assert reservation.lease is not None
    source = pdf_source(assets, payload)

    with pytest.raises(RuntimeError, match="PDF"):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-trailing-pdf-request",
        )

    assert source.stream.closed is True
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        copied_asset_count = conn.execute(
            "SELECT COUNT(*) FROM web_asset_files WHERE id != ?",
            (SOURCE_ASSET_ID,),
        ).fetchone()[0]
    assert copied_asset_count == 0
    assert not list((tmp_path / "private-web-assets" / "objects").glob("*.blob"))
    assert not list((tmp_path / "private-web-assets" / ".staging").glob("*"))


@pytest.mark.parametrize(
    ("kind", "extension", "content_type"),
    (
        ("pdf_to_word_text", ".pdf", "application/pdf"),
        ("pdf_split", ".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("pdf_split", ".txt", "text/plain"),
    ),
)
def test_finalizer_rejects_noncanonical_document_specs(tmp_path, monkeypatch, kind: str, extension: str, content_type: str) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload, kind=kind)
    reservation = reserve(assets, payload, key=f"document-finalization-{kind}-0001")
    assert reservation.lease is not None
    source = pdf_source(assets, payload, kind=kind, extension=extension, content_type=content_type)

    with pytest.raises(RuntimeError):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id=f"document-finalization-{kind}-request",
        )

    assert source.stream.closed is True
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        copied_asset_count = conn.execute(
            "SELECT COUNT(*) FROM web_asset_files WHERE id != ?",
            (SOURCE_ASSET_ID,),
        ).fetchone()[0]
    assert copied_asset_count == 0


@pytest.mark.parametrize(
    "disabled_gate",
    (
        "WEBAPP_ASSET_VAULT_ENABLED",
        "WEBAPP_DOCUMENT_OPERATIONS_ENABLED",
        "WEBAPP_DOCUMENT_OPERATION_EXPORT_ENABLED",
    ),
)
def test_finalizer_rechecks_every_effective_feature_gate(tmp_path, monkeypatch, disabled_gate: str) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key=f"document-finalization-gate-{disabled_gate}-0001")
    assert reservation.lease is not None
    source = pdf_source(assets, payload)
    monkeypatch.setenv(disabled_gate, "false")

    with pytest.raises(HTTPException) as rejected:
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id=f"document-finalization-gate-{disabled_gate}-request",
        )

    assert rejected.value.status_code == 503
    assert source.stream.closed is True
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        copied_asset_count = conn.execute(
            "SELECT COUNT(*) FROM web_asset_files WHERE id != ?",
            (SOURCE_ASSET_ID,),
        ).fetchone()[0]
    assert copied_asset_count == 0


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("account_id", "99999999-9999-4999-8999-999999999999"),
        ("sha256", "0" * 64),
        ("byte_size", 1),
        ("project_id", "99999999-9999-4999-8999-999999999999"),
        ("original_filename", "another-safe.pdf"),
    ),
)
def test_finalizer_rejects_source_fields_that_do_not_match_its_lease(tmp_path, monkeypatch, field: str, value) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key=f"document-finalization-source-{field}-0001")
    assert reservation.lease is not None
    source = replace(pdf_source(assets, payload), **{field: value})

    with pytest.raises(RuntimeError, match="khớp"):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id=f"document-finalization-source-{field}-request",
        )

    assert source.stream.closed is True
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        copied_asset_count = conn.execute(
            "SELECT COUNT(*) FROM web_asset_files WHERE id != ?",
            (SOURCE_ASSET_ID,),
        ).fetchone()[0]
    assert copied_asset_count == 0


def test_finalizer_rehashes_the_pinned_stream_and_rechecks_the_operation_row(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key="document-finalization-rehash-row-0001")
    assert reservation.lease is not None
    source = replace(pdf_source(assets, payload), stream=BytesIO(payload + b"unexpected trailing bytes"))

    with pytest.raises(RuntimeError, match="vượt"):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-rehash-stream-request",
        )

    assert source.stream.closed is True
    with db.transaction() as conn:
        conn.execute("UPDATE web_document_operations SET sha256=? WHERE id=?", ("0" * 64, OPERATION_ID))
    row_source = pdf_source(assets, payload)
    with pytest.raises(RuntimeError, match="khớp"):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=row_source,
            request_id="document-finalization-rehash-row-request",
        )

    assert row_source.stream.closed is True
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        copied_asset_count = conn.execute(
            "SELECT COUNT(*) FROM web_asset_files WHERE id != ?",
            (SOURCE_ASSET_ID,),
        ).fetchone()[0]
        audit_count = conn.execute(
            "SELECT COUNT(*) FROM web_audit_events WHERE action='web.document_operation.export_to_asset_vault'"
        ).fetchone()[0]
    assert copied_asset_count == 0
    assert audit_count == 0
    assert not list((tmp_path / "private-web-assets" / "objects").glob("*.blob"))
    assert not list((tmp_path / "private-web-assets" / ".staging").glob("*"))


@pytest.mark.parametrize(
    ("column", "value"),
    (
        ("content_type", "application/octet-stream"),
        ("storage_key", "outputs/" + "a" * 32 + ".docx"),
        ("original_filename", "toan-aas-pdf-split.pdf"),
    ),
    ids=("content-type", "storage-key-suffix", "raw-original-filename"),
)
def test_finalizer_rejects_operation_output_metadata_changed_after_source_descriptor(
    tmp_path,
    monkeypatch,
    column: str,
    value: str,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key=f"document-finalization-toctou-{column}-0001")
    assert reservation.lease is not None
    source = pdf_source(assets, payload)
    with db.transaction() as conn:
        conn.execute(
            f"UPDATE web_document_operations SET {column}=? WHERE id=?",
            (value, OPERATION_ID),
        )

    with pytest.raises(RuntimeError, match="khớp"):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id=f"document-finalization-toctou-{column}-request",
        )

    assert source.stream.closed is True
    assert_document_export_remains_copying(tmp_path)


def test_close_value_error_does_not_mask_post_promotion_validation_failure(
    tmp_path,
    monkeypatch,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key="document-finalization-close-value-error-0001")
    assert reservation.lease is not None
    source = replace(
        pdf_source(assets, payload),
        stream=CloseValueErrorStream(payload),
    )
    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_document_operations SET original_filename=? WHERE id=?",
            ("toan-aas-pdf-split.pdf", OPERATION_ID),
        )

    with pytest.raises(RuntimeError, match="khớp") as rejected:
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-close-value-error-request",
        )

    assert "synthetic close failure" not in str(rejected.value)
    assert source.stream.closed is True
    assert_document_export_remains_copying(tmp_path)


def test_finalizer_never_overwrites_an_unowned_destination_collision(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key="document-finalization-destination-collision-0001")
    assert reservation.lease is not None
    collision = tmp_path / "private-web-assets" / reservation.lease.pending_storage_key
    collision.parent.mkdir(parents=True, exist_ok=True)
    collision.write_bytes(b"unowned private blob")
    source = pdf_source(assets, payload)

    with pytest.raises(RuntimeError, match="độc quyền"):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-destination-collision-request",
        )

    assert source.stream.closed is True
    assert collision.read_bytes() == b"unowned private blob"
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        copied_asset_count = conn.execute(
            "SELECT COUNT(*) FROM web_asset_files WHERE id != ?",
            (SOURCE_ASSET_ID,),
        ).fetchone()[0]
    assert copied_asset_count == 0
    assert not list((tmp_path / "private-web-assets" / ".staging").glob("*"))


def test_finalizer_samples_its_fence_time_only_after_holding_the_write_lock(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key="document-finalization-lock-time-0001")
    assert reservation.lease is not None
    real_transaction = assets.transaction
    real_utc_now = assets.utc_now
    write_lock_held = False

    @contextmanager
    def transaction_with_lock_signal():
        nonlocal write_lock_held
        with real_transaction() as conn:
            write_lock_held = True
            yield conn

    def utc_now_after_lock() -> str:
        assert write_lock_held is True
        return real_utc_now()

    monkeypatch.setattr(assets, "transaction", transaction_with_lock_signal)
    monkeypatch.setattr(assets, "utc_now", utc_now_after_lock)
    finalized = assets.finalize_document_operation_asset_export(
        lease=reservation.lease,
        source=pdf_source(assets, payload),
        request_id="document-finalization-lock-time-request",
    )

    assert finalized.state == "completed"


def test_pending_quota_can_use_the_finalizer_fence_time(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key="document-finalization-quota-time-0001")
    assert reservation.lease is not None
    expiry = datetime.fromisoformat(reservation.lease.expires_at)

    with db.transaction() as conn:
        assert assets._pending_document_operation_asset_export_bytes(
            conn,
            ACCOUNT_ID,
            reference_now=expiry - timedelta(seconds=1),
        ) == len(payload)
        assert assets._pending_document_operation_asset_export_bytes(
            conn,
            ACCOUNT_ID,
            reference_now=expiry + timedelta(seconds=1),
        ) == 0


def test_finalizer_rolls_back_when_quota_is_exhausted_after_reservation(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key="document-finalization-quota-race-0001")
    assert reservation.lease is not None
    monkeypatch.setenv("WEBAPP_ASSET_VAULT_QUOTA_MB", "1")
    now = db.utc_now()
    with db.transaction() as conn:
        conn.execute(
            """INSERT INTO web_asset_files
               (id, account_id, project_id, display_name, original_filename, extension,
                content_type, byte_size, sha256, storage_key, state, lifecycle_revision,
                created_at, updated_at, archived_at)
               VALUES (?, ?, NULL, ?, ?, '.pdf', 'application/pdf', ?, ?, ?, 'active', 1, ?, ?, NULL)""",
            (
                "44444444-4444-4444-8444-444444444444",
                ACCOUNT_ID,
                "Quota filler",
                "quota-filler.pdf",
                1024 * 1024,
                "f" * 64,
                "objects/" + "4" * 32 + ".blob",
                now,
                now,
            ),
        )
    source = pdf_source(assets, payload)

    with pytest.raises(HTTPException) as blocked:
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id="document-finalization-quota-race-request",
        )

    assert blocked.value.status_code == 413
    assert source.stream.closed is True
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        relation_state = conn.execute(
            "SELECT state FROM web_document_operation_asset_exports WHERE operation_id=?",
            (OPERATION_ID,),
        ).fetchone()[0]
        copied_asset_count = conn.execute(
            "SELECT COUNT(*) FROM web_asset_files WHERE id NOT IN (?, ?)",
            (SOURCE_ASSET_ID, "44444444-4444-4444-8444-444444444444"),
        ).fetchone()[0]
        audit_count = conn.execute(
            "SELECT COUNT(*) FROM web_audit_events WHERE action='web.document_operation.export_to_asset_vault'"
        ).fetchone()[0]
    assert relation_state == "copying"
    assert copied_asset_count == 0
    assert audit_count == 0
    assert not list((tmp_path / "private-web-assets" / "objects").glob("*.blob"))
    assert not list((tmp_path / "private-web-assets" / ".staging").glob("*"))


def test_stale_pdf_finalizer_cannot_overwrite_a_reclaimed_completed_export(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    first = reserve(assets, payload, key="document-finalization-stale-first-0001")
    assert first.lease is not None
    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_document_operation_asset_exports SET lease_expires_at=? WHERE operation_id=?",
            ("1970-01-01T00:00:00+00:00", OPERATION_ID),
        )
    reclaimed = reserve(assets, payload, key="document-finalization-stale-reclaimed-0001")
    assert reclaimed.lease is not None

    stale_source = pdf_source(assets, payload)
    with pytest.raises(RuntimeError, match="lease"):
        assets.finalize_document_operation_asset_export(
            lease=first.lease,
            source=stale_source,
            request_id="document-finalization-stale-late-request",
        )

    assert stale_source.stream.closed is True
    assert not (tmp_path / "private-web-assets" / first.lease.pending_storage_key).exists()
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        still_copying = conn.execute(
            "SELECT state, lease_generation, lease_token FROM web_document_operation_asset_exports WHERE operation_id=?",
            (OPERATION_ID,),
        ).fetchone()
        stale_audit_count = conn.execute(
            "SELECT COUNT(*) FROM web_audit_events WHERE action='web.document_operation.export_to_asset_vault'"
        ).fetchone()[0]
    assert still_copying == ("copying", reclaimed.lease.generation, reclaimed.lease.token)
    assert stale_audit_count == 0

    completed = assets.finalize_document_operation_asset_export(
        lease=reclaimed.lease,
        source=pdf_source(assets, payload),
        request_id="document-finalization-stale-reclaimed-request",
    )
    assert completed.asset is not None
    with sqlite3.connect(tmp_path / "document-export-finalization-pdf.db") as conn:
        relation = conn.execute(
            "SELECT asset_id, state FROM web_document_operation_asset_exports WHERE operation_id=?",
            (OPERATION_ID,),
        ).fetchone()
        asset_count = conn.execute("SELECT COUNT(*) FROM web_asset_files").fetchone()[0]
    assert relation == (completed.asset["id"], "completed")
    assert asset_count == 2
    assert not (tmp_path / "private-web-assets" / first.lease.pending_storage_key).exists()


def test_reconciler_keeps_live_document_export_object_then_removes_it_after_lease_expires(
    tmp_path,
    monkeypatch,
) -> None:
    """A fenced document-export object is protected only for its live lease."""

    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key="document-export-reconciler-pending-0001")
    assert reservation.lease is not None
    pending_object = tmp_path / "private-web-assets" / reservation.lease.pending_storage_key
    pending_object.parent.mkdir(parents=True, exist_ok=True)
    pending_object.write_bytes(payload)
    old_timestamp = time.time() - assets.ORPHAN_RETENTION_SECONDS - 2
    os.utime(pending_object, (old_timestamp, old_timestamp))

    assets.reconcile_asset_vault_storage()

    assert pending_object.is_file()
    with db.transaction() as conn:
        conn.execute(
            "UPDATE web_document_operation_asset_exports SET lease_expires_at=? WHERE operation_id=?",
            ("1970-01-01T00:00:00+00:00", OPERATION_ID),
        )

    assets.reconcile_asset_vault_storage()

    assert not pending_object.exists()


def test_reconciler_never_deletes_an_active_asset_blob(tmp_path, monkeypatch) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    active_object = tmp_path / "private-web-assets" / "objects" / ("1" * 32 + ".blob")
    active_object.parent.mkdir(parents=True, exist_ok=True)
    active_object.write_bytes(payload)
    old_timestamp = time.time() - assets.ORPHAN_RETENTION_SECONDS - 2
    os.utime(active_object, (old_timestamp, old_timestamp))

    assets.reconcile_asset_vault_storage()

    assert active_object.is_file()


@pytest.mark.parametrize("directory_name", (".staging", "objects"))
def test_document_finalizer_rejects_symlinked_private_parent_without_external_write(
    tmp_path,
    monkeypatch,
    directory_name: str,
) -> None:
    db, assets = load_modules(tmp_path, monkeypatch)
    payload = pdf_bytes()
    seed_completed_document_operation(db, payload=payload)
    reservation = reserve(assets, payload, key=f"document-parent-{directory_name}-0001")
    assert reservation.lease is not None
    root = tmp_path / "private-web-assets"
    external = tmp_path / f"external-{directory_name.removeprefix('.')}"
    external.mkdir()
    sentinel = external / "sentinel"
    sentinel.write_bytes(b"must remain untouched")
    try:
        (root / directory_name).symlink_to(external, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("directory symlinks are unavailable in this environment")

    source = pdf_source(assets, payload)
    with pytest.raises(RuntimeError, match="thư mục riêng tư"):
        assets.finalize_document_operation_asset_export(
            lease=reservation.lease,
            source=source,
            request_id=f"document-parent-{directory_name}-request",
        )

    assert source.stream.closed is True
    assert sentinel.read_bytes() == b"must remain untouched"
    assert list(external.iterdir()) == [sentinel]


@pytest.mark.parametrize("directory_name", (".staging", "objects"))
def test_reconciler_rejects_symlinked_private_parent_without_external_delete(
    tmp_path,
    monkeypatch,
    directory_name: str,
) -> None:
    _db, assets = load_modules(tmp_path, monkeypatch)
    root = tmp_path / "private-web-assets"
    external = tmp_path / f"external-reconcile-{directory_name.removeprefix('.')}"
    external.mkdir()
    sentinel = external / "old-orphan"
    sentinel.write_bytes(b"must remain untouched")
    old_timestamp = time.time() - assets.ORPHAN_RETENTION_SECONDS - 2
    os.utime(sentinel, (old_timestamp, old_timestamp))
    try:
        (root / directory_name).symlink_to(external, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("directory symlinks are unavailable in this environment")

    with pytest.raises(RuntimeError, match="thư mục riêng tư"):
        assets.reconcile_asset_vault_storage()

    assert sentinel.read_bytes() == b"must remain untouched"
