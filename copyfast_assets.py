"""Private, Web-owned Asset Vault.

The vault is intentionally a small, independent storage product: signed Web
accounts can safely keep files and attach them to Web Projects without using a
browser-supplied filesystem path, public static URL, localStorage identity, or
an external execution service.  This module owns metadata and private blobs
only; it does not represent a generated job result or an account balance.
"""

from __future__ import annotations

import codecs
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import tempfile
from types import MappingProxyType
import unicodedata
import uuid
import warnings
from typing import Annotated, Any, BinaryIO, Iterator
from urllib.parse import quote
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pypdf import PdfReader
from starlette.background import BackgroundTask

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import (
    asset_vault_directory,
    asset_vault_enabled,
    asset_vault_video_preview_enabled,
    audio_asset_operation_export_enabled,
    audio_asset_operations_enabled,
    document_operation_export_enabled,
    document_operations_enabled,
    ensure_copyfast_schema,
    image_operation_export_enabled,
    image_operations_enabled,
    transaction,
    utc_now,
)


router = APIRouter(prefix="/api/v1/asset-vault", tags=["Web Asset Vault"])

ACTIVE_STATE = "active"
ARCHIVED_STATE = "archived"
UNAVAILABLE_STATE = "unavailable"
VISIBLE_STATES = frozenset({ACTIVE_STATE, ARCHIVED_STATE})
ALL_STATES = frozenset({ACTIVE_STATE, ARCHIVED_STATE, UNAVAILABLE_STATE})
# Typed operation pickers must stay exact and server-side.  Audio is a
# separate allowlisted family for Audio Asset Operations; it is deliberately
# not implemented as a loose ``audio/*`` query.
REFERENCE_KINDS = frozenset({"all", "pdf", "image", "subtitle", "audio", "video_transform", "video_poster", "video_preview"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
ASSET_ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
STORAGE_KEY_PATTERN = re.compile(r"^objects/[0-9a-f]{32}\.blob$")
PENDING_MARKER_KEY = "_web_asset_vault_pending"
PENDING_SECONDS = 5 * 60
ORPHAN_RETENTION_SECONDS = 60 * 60
IMAGE_OPERATION_EXPORT_LEASE_SECONDS = 5 * 60
DOCUMENT_OPERATION_ASSET_EXPORT_LEASE_SECONDS = 5 * 60
AUDIO_OPERATION_ASSET_EXPORT_LEASE_SECONDS = 5 * 60
CHUNK_BYTES = 1024 * 1024
IMAGE_OPERATION_EXPORT_KINDS = frozenset({
    "image_resize",
    "image_enhance",
    "image_background_cleanup",
    "image_brand_overlay",
})
# This map is deliberately local instead of importing the Document Operations
# module: the finalizer must independently enforce the exact sealed output
# contract without creating an import cycle or accepting browser metadata.
DOCUMENT_OPERATION_ASSET_EXPORT_SPECS = MappingProxyType({
    "pdf_split": (".pdf", "application/pdf", "toan-aas-pdf-split.pdf"),
    "pdf_merge": (".pdf", "application/pdf", "toan-aas-pdf-merged.pdf"),
    "pdf_optimize": (".pdf", "application/pdf", "toan-aas-pdf-optimized.pdf"),
    "image_to_pdf": (".pdf", "application/pdf", "toan-aas-images.pdf"),
    "pdf_to_word_text": (
        ".docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "toan-aas-pdf-text.docx",
    ),
    "pdf_ocr_word": (
        ".docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "toan-aas-pdf-ocr.docx",
    ),
    "image_ocr": (".txt", "text/plain; charset=utf-8", "toan-aas-image-ocr.txt"),
    "pdf_ocr": (".txt", "text/plain; charset=utf-8", "toan-aas-pdf-ocr.txt"),
})
DOCUMENT_OPERATION_ASSET_EXPORT_OUTPUT_FILENAMES = MappingProxyType({
    "pdf_merge": "toan-aas-merged-pdf.pdf",
    "pdf_optimize": "toan-aas-optimized-pdf.pdf",
    "image_to_pdf": "toan-aas-images.pdf",
    "pdf_to_word_text": "toan-aas-pdf-text.docx",
    "pdf_ocr_word": "toan-aas-pdf-ocr.docx",
    "image_ocr": "toan-aas-image-ocr.txt",
    "pdf_ocr": "toan-aas-pdf-ocr.txt",
})
PDF_EOF_SCAN_BYTES = 64 * 1024
PDF_TRAILING_WHITESPACE = b"\x00\x09\x0a\x0c\x0d\x20"
DOCUMENT_OPERATION_ASSET_EXPORT_TEXT_MAX_BYTES = 2 * 1024 * 1024
DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_MEMBERS = 200
DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_UNCOMPRESSED_BYTES = 8 * 1024 * 1024
DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_CENTRAL_DIRECTORY_BYTES = 1024 * 1024
DOCX_CLASSIC_EOCD_BYTES = 22
DOCX_MAX_COMMENT_BYTES = 65_535
DOCX_RELATIONSHIPS_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/relationships"
DOCX_CONTENT_TYPES_NAMESPACE = "http://schemas.openxmlformats.org/package/2006/content-types"
DOCX_OFFICE_DOCUMENT_RELATIONSHIP = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
)
DOCX_WORD_MAIN_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)
VIDEO_PREVIEW_MAX_BYTES = 20 * 1024 * 1024
VIDEO_PREVIEW_MEDIA_PAIRS = frozenset({
    (".mp4", "video/mp4"),
    (".webm", "video/webm"),
})
MAX_DOCX_ARCHIVE_MEMBERS = 2_000
MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024

ASSET_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm",
    ".mp3", ".wav", ".m4a", ".ogg", ".pdf", ".txt", ".srt", ".vtt", ".docx",
})
CANONICAL_MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".ogg": "audio/ogg",
    ".pdf": "application/pdf", ".txt": "text/plain", ".srt": "application/x-subrip", ".vtt": "text/vtt",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ACCEPTED_MIME_BY_EXTENSION = {
    ".jpg": frozenset({"image/jpeg"}), ".jpeg": frozenset({"image/jpeg"}),
    ".png": frozenset({"image/png"}), ".webp": frozenset({"image/webp"}),
    ".mp4": frozenset({"video/mp4"}), ".mov": frozenset({"video/quicktime"}),
    ".webm": frozenset({"video/webm"}), ".mp3": frozenset({"audio/mpeg"}),
    ".wav": frozenset({"audio/wav", "audio/x-wav"}), ".m4a": frozenset({"audio/mp4"}),
    ".ogg": frozenset({"audio/ogg", "application/ogg"}), ".pdf": frozenset({"application/pdf"}),
    ".txt": frozenset({"text/plain"}), ".srt": frozenset({"application/x-subrip", "text/plain"}),
    ".vtt": frozenset({"text/vtt", "text/plain"}),
    ".docx": frozenset({"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}),
}
TEXT_EXTENSIONS = frozenset({".txt", ".srt", ".vtt"})
SEARCH_SECRET_PATTERN = re.compile(
    r"\b(?:api[ _-]?(?:key|token)|access[ _-]?token|refresh[ _-]?token|"
    r"client[ _-]?secret|password|passphrase|authorization)\b\s*(?:[:=]|\bis\b)\s*"
    r"(?:bearer\s+)?[A-Za-z0-9_./+=:-]{8,}",
    re.IGNORECASE,
)
CARD_LIKE_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _require_enabled() -> None:
    if not asset_vault_enabled():
        raise HTTPException(status_code=503, detail="Asset Vault chưa được bật cho môi trường này")


def _require_image_operation_export_enabled() -> None:
    """Keep the internal export boundary closed unless all storage gates hold."""

    _require_enabled()
    if not image_operations_enabled() or not image_operation_export_enabled():
        raise HTTPException(status_code=503, detail="Lưu PNG Image Operations vào Asset Vault chưa được bật")


def _require_document_operation_asset_export_enabled() -> None:
    """Keep completed Document Operation copies behind every private gate."""

    _require_enabled()
    if not document_operations_enabled() or not document_operation_export_enabled():
        raise HTTPException(status_code=503, detail="Lưu Document Operations vào Asset Vault chưa được bật")


def _require_audio_operation_asset_export_enabled() -> None:
    """Keep Audio Operation output copies behind all three private gates."""

    _require_enabled()
    if not audio_asset_operations_enabled() or not audio_asset_operation_export_enabled():
        raise HTTPException(status_code=503, detail="Lưu Audio Asset Operations vào Asset Vault chưa được bật")


def _maximum_bytes() -> int:
    raw = os.environ.get("WEBAPP_ASSET_VAULT_MAX_FILE_MB", "25").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 25
    # A small, explicit ceiling keeps every integrity verification bounded.
    return max(1, min(megabytes, 100)) * 1024 * 1024


def _maximum_account_bytes() -> int:
    raw = os.environ.get("WEBAPP_ASSET_VAULT_QUOTA_MB", "250").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 250
    # Permit a 1 MB tenant quota for tests/small accounts; silently raising a
    # requested low quota would weaken an operator's storage safety policy.
    return max(1, min(megabytes, 5_000)) * 1024 * 1024


def _validate_id(value: str, *, label: str) -> str:
    candidate = str(value or "").strip()
    if not ASSET_ID_PATTERN.fullmatch(candidate):
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ")
    return str(uuid.UUID(candidate))


def _idempotency_key(value: str | None) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Idempotency key không hợp lệ")
    return key


def _image_operation_id(value: str) -> str:
    candidate = str(value or "").strip()
    if not ASSET_ID_PATTERN.fullmatch(candidate):
        raise HTTPException(status_code=422, detail="Mã thao tác ảnh không hợp lệ")
    return str(uuid.UUID(candidate))


def _document_operation_id(value: str) -> str:
    candidate = str(value or "").strip()
    if not ASSET_ID_PATTERN.fullmatch(candidate):
        raise HTTPException(status_code=422, detail="Mã thao tác tài liệu không hợp lệ")
    return str(uuid.UUID(candidate))


def _audio_operation_id(value: str) -> str:
    candidate = str(value or "").strip()
    if not ASSET_ID_PATTERN.fullmatch(candidate):
        raise HTTPException(status_code=422, detail="Mã thao tác audio không hợp lệ")
    return str(uuid.UUID(candidate))


def _export_request_fingerprint(value: str) -> str:
    candidate = str(value or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", candidate):
        raise HTTPException(status_code=422, detail="Dấu vân tay export không hợp lệ")
    return candidate


@dataclass(frozen=True)
class ImageOperationAssetExportLease:
    """One attempt-owned, fenced reservation for a private PNG copy."""

    account_id: str
    operation_id: str
    generation: int
    token: str
    expires_at: str
    pending_storage_key: str
    reserved_bytes: int
    request_fingerprint: str


@dataclass(frozen=True)
class ImageOperationAssetExportReservation:
    """A reservation result without an Asset Vault snapshot cache."""

    state: str
    lease: ImageOperationAssetExportLease | None = None


@dataclass
class ImageOperationAssetExportSource:
    """One already-verified Image Operation output pinned to an open stream.

    The Image Operations boundary constructs this only from its owner-scoped
    database row and keeps ``stream`` open until this exporter closes it.  No
    caller-provided path, URL or browser bytes can enter the Vault copy path.
    """

    account_id: str
    operation_id: str
    kind: str
    project_id: str | None
    original_filename: str
    byte_size: int
    sha256: str
    width: int
    height: int
    stream: BinaryIO


@dataclass(frozen=True)
class ImageOperationAssetExportFinalization:
    """Fresh public Asset Vault receipt after a completed fenced copy."""

    state: str
    asset: dict[str, Any] | None


@dataclass(frozen=True)
class DocumentOperationAssetExportLease:
    """One attempt-owned, fenced reservation for a Document Operation copy."""

    account_id: str
    operation_id: str
    generation: int
    token: str
    expires_at: str
    pending_storage_key: str
    reserved_bytes: int
    request_fingerprint: str


@dataclass(frozen=True)
class DocumentOperationAssetExportReservation:
    """A document-export reservation without an Asset Vault snapshot cache."""

    state: str
    lease: DocumentOperationAssetExportLease | None = None


@dataclass(frozen=True)
class DocumentOperationAssetExportSource:
    """One server-derived Document Operation output pinned to an open stream.

    The Document Operations boundary constructs this descriptor from its
    owner-scoped completed row.  The finalizer owns ``stream`` after entry and
    never accepts a browser path, URL, or replacement bytes.
    """

    account_id: str = field(repr=False)
    operation_id: str = field(repr=False)
    kind: str
    project_id: str | None = field(repr=False)
    original_filename: str = field(repr=False)
    extension: str
    content_type: str
    byte_size: int
    sha256: str = field(repr=False)
    stream: BinaryIO = field(repr=False, compare=False)


@dataclass(frozen=True)
class DocumentOperationAssetExportFinalization:
    """Fresh public Asset Vault receipt for a completed Document export."""

    state: str
    asset: dict[str, Any] | None


@dataclass(frozen=True)
class AudioOperationAssetExportLease:
    account_id: str
    operation_id: str
    generation: int
    token: str
    expires_at: str
    pending_storage_key: str
    reserved_bytes: int
    request_fingerprint: str


@dataclass(frozen=True)
class AudioOperationAssetExportReservation:
    state: str
    lease: AudioOperationAssetExportLease | None = None


@dataclass(frozen=True)
class AudioOperationAssetExportSource:
    """A server-derived, pre-opened completed Audio Operation output."""

    account_id: str = field(repr=False)
    operation_id: str = field(repr=False)
    kind: str
    project_id: str | None = field(repr=False)
    original_filename: str = field(repr=False)
    target_format: str
    extension: str
    content_type: str
    byte_size: int
    sha256: str = field(repr=False)
    duration_seconds: float
    duration_ms: int
    channels: int
    sample_rate: int
    codec: str
    format_name: str
    stream: BinaryIO = field(repr=False, compare=False)


@dataclass(frozen=True)
class AudioOperationAssetExportFinalization:
    state: str
    asset: dict[str, Any] | None


class AssetRestoreRequest(BaseModel):
    """The narrow, replay-safe intent to reactivate one archived Web blob."""

    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, le=2_147_483_647)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str) -> str:
        return _idempotency_key(value)


class AssetArchiveRequest(BaseModel):
    """The compare-and-set intent to archive one active Web blob.

    Archive is a lifecycle mutation just like restore. Keeping the revision in
    the JSON body prevents a stale browser action from overwriting a newer
    lifecycle decision.
    """

    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, le=2_147_483_647)


def _safe_filename(value: str | None) -> tuple[str, str]:
    name = str(value or "").strip()
    has_control = any(ord(character) < 32 or ord(character) == 127 for character in name)
    if (
        not name
        or len(name) > 180
        or has_control
        or name.startswith(".")
        or "/" in name
        or "\\" in name
        or name in {".", ".."}
    ):
        raise HTTPException(status_code=422, detail="Tên tệp không hợp lệ")
    extension = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in ASSET_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Định dạng tệp chưa được Asset Vault hỗ trợ")
    return name, extension


def _safe_display_name(value: str | None, *, source_name: str) -> str:
    compact = re.sub(r"\s+", " ", str(value or "")).strip()
    if not compact:
        compact = source_name.rsplit(".", 1)[0] or "Tệp Web"
    has_control = any(ord(character) < 32 or ord(character) == 127 for character in compact)
    if has_control or not 1 <= len(compact) <= 120:
        raise HTTPException(status_code=422, detail="Tên hiển thị cần từ 1 đến 120 ký tự hợp lệ")
    return compact


def _list_search(value: str | None) -> str:
    """Normalize a short private-library search term without retaining secrets.

    Asset names themselves remain owner-scoped metadata, but a query reaches
    request logs/proxies more readily than a body.  Keep the library search
    intentionally small and reject credential/card-shaped input rather than
    letting the Portal turn the Vault into a secret lookup surface.
    """
    query = re.sub(r"\s+", " ", str(value or "")).strip()
    if "\x00" in query or len(query) > 100:
        raise HTTPException(status_code=422, detail="Từ khóa tìm Asset Vault tối đa 100 ký tự hợp lệ")
    if query and (SEARCH_SECRET_PATTERN.search(query) or CARD_LIKE_PATTERN.search(query)):
        raise HTTPException(status_code=422, detail="Từ khóa tìm Asset Vault không nhận secret, token hoặc số thẻ")
    return query


def _reference_kind(value: str | None) -> str:
    """Return the narrow, server-side type filter used by native pickers.

    The Asset Vault remains a general library.  Native document and image
    operations, however, must not fetch an arbitrary first page and attempt
    to infer a usable source in the browser.  Keep the vocabulary allowlisted
    so a caller cannot turn it into a SQL fragment or an unbounded MIME query.
    """
    selected = str(value or "all").strip().lower()
    if selected not in REFERENCE_KINDS:
        raise HTTPException(status_code=422, detail="Loại reference Asset Vault không hợp lệ")
    return selected


def _canonical_media_type(extension: str, supplied: str | None) -> str:
    canonical = CANONICAL_MIME_BY_EXTENSION.get(extension)
    accepted = ACCEPTED_MIME_BY_EXTENSION.get(extension)
    received = str(supplied or "application/octet-stream").split(";", 1)[0].strip().lower() or "application/octet-stream"
    if not canonical or not accepted:
        raise HTTPException(status_code=415, detail="Định dạng tệp chưa được Asset Vault hỗ trợ")
    if received != "application/octet-stream" and received not in accepted:
        raise HTTPException(status_code=415, detail="MIME không khớp với định dạng tệp")
    return canonical


def _storage_path(root: Path, storage_key: str) -> Path:
    if not STORAGE_KEY_PATTERN.fullmatch(storage_key):
        raise RuntimeError("Storage key Asset Vault không hợp lệ")
    # Do not resolve the final blob path here.  Resolving it would follow a
    # final-component symlink before the descriptor-pinning check below gets a
    # chance to reject it.  The storage-key grammar is fixed to
    # ``objects/<random>.blob``, so joining it underneath the resolved root is
    # both traversal-safe and preserves the physical final component for
    # ``lstat``/``O_NOFOLLOW``.
    resolved_root = root.resolve()
    candidate = resolved_root / storage_key
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise RuntimeError("Storage key Asset Vault vượt ngoài thư mục riêng") from exc
    return candidate


def _private_asset_vault_child_directory(root: Path, name: str) -> Path:
    """Return one safe Vault-owned generated directory without following links."""

    if name not in {".staging", "objects"}:
        raise RuntimeError("Thư mục riêng tư Asset Vault không hợp lệ")
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError("Không thể xác minh thư mục riêng tư Asset Vault") from exc
    directory = root / name

    def checked_lstat() -> os.stat_result | None:
        try:
            metadata = os.lstat(directory)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise RuntimeError("Không thể xác minh thư mục riêng tư Asset Vault") from exc
        is_reparse_point = bool(
            getattr(metadata, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
        )
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode) or is_reparse_point:
            raise RuntimeError("Thư mục riêng tư Asset Vault không hợp lệ")
        return metadata

    checked_lstat()
    try:
        directory.mkdir(parents=False, exist_ok=True)
    except OSError as exc:
        raise RuntimeError("Không thể tạo thư mục riêng tư Asset Vault") from exc
    if checked_lstat() is None:
        raise RuntimeError("Không thể xác minh thư mục riêng tư Asset Vault")
    try:
        resolved_directory = directory.resolve(strict=True)
        resolved_directory.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise RuntimeError("Thư mục riêng tư Asset Vault không hợp lệ") from exc
    return directory


def _staging_path(root: Path) -> Path:
    directory = _private_asset_vault_child_directory(root, ".staging")
    return directory / f"{uuid.uuid4().hex}.upload"


def _asset_public(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "project_id": str(row[1]) if row[1] else None,
        "display_name": str(row[2]),
        "original_filename": str(row[3]),
        "extension": str(row[4]),
        "content_type": str(row[5]),
        "byte_size": int(row[6]),
        "state": str(row[7]),
        "created_at": str(row[8]),
        "updated_at": str(row[9]),
        "archived_at": str(row[10]) if row[10] else None,
    }


def _asset_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy tệp thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_ASSET_NOT_FOUND",
    )


def _asset_unavailable() -> dict[str, Any]:
    return envelope(
        False,
        "Tệp không còn sẵn sàng để tải xuống. Hãy tải lại hoặc liên hệ hỗ trợ.",
        status_name="guarded",
        error_code="WEB_ASSET_UNAVAILABLE",
    )


def _asset_lifecycle_conflict() -> dict[str, Any]:
    return envelope(
        False,
        "Tệp đã thay đổi vòng đời. Hãy tải lại thông tin trước khi khôi phục.",
        status_name="guarded",
        error_code="WEB_ASSET_LIFECYCLE_CONFLICT",
    )


def _asset_restore_unavailable() -> dict[str, Any]:
    """A deliberately non-forensic restore failure projection.

    The browser receives neither a storage location nor an integrity detail.
    Operators can correlate the bounded audit action with server diagnostics
    without turning the public API into an oracle for private blob layout.
    """
    return envelope(
        False,
        "Không thể khôi phục tệp an toàn. Tệp đã được đánh dấu không sẵn sàng.",
        status_name="guarded",
        error_code="WEB_ASSET_UNAVAILABLE",
    )


def _row_for_account(conn, asset_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, project_id, display_name, original_filename, extension, content_type,
                  byte_size, state, created_at, updated_at, archived_at, sha256, storage_key,
                  lifecycle_revision
           FROM web_asset_files WHERE id=? AND account_id=?""",
        (asset_id, account_id),
    ).fetchone()


def _video_preview_source_allowed(row: tuple[Any, ...]) -> bool:
    """Return whether one private row is safe for the Blob video inspector.

    Keep the source allowlist on the server and pair extension/MIME exactly.
    Browser codec support is intentionally not inferred here: a source that
    passes this storage contract can still be guarded by the browser decoder.
    """

    try:
        byte_size = int(row[6])
    except (IndexError, TypeError, ValueError):
        return False
    try:
        media_pair = (str(row[4] or "").lower(), str(row[5] or "").lower())
    except IndexError:
        return False
    return 0 < byte_size <= VIDEO_PREVIEW_MAX_BYTES and media_pair in VIDEO_PREVIEW_MEDIA_PAIRS


def _visible_asset(row: tuple[Any, ...]) -> dict[str, Any]:
    return _asset_public(row[:11])


def _lifecycle_revision(row: tuple[Any, ...]) -> int:
    """Read the additive optimistic-concurrency token from a private row."""
    try:
        return max(1, int(row[13]))
    except (IndexError, TypeError, ValueError):
        # Schema initialization always supplies this column.  Fail closed to
        # the first revision only for a legacy test/durable row, never by
        # interpreting a timestamp or caller-provided value as a revision.
        return 1


def _lifecycle_reference_summary(conn, *, asset_id: str, account_id: str) -> dict[str, Any]:
    """Return only owner-scoped counts and reasons for retained references.

    This deliberately omits case/project/operation identifiers, blob keys,
    hashes and filenames. Support evidence is a hard retention blocker for a
    future purge workflow, not a reason to break archived-download behavior or
    deny a safe restore today.
    """
    definitions = (
        (
            "support_evidence_retention",
            True,
            "SELECT COUNT(*) FROM web_support_case_attachments WHERE asset_id=? AND account_id=?",
            (asset_id, account_id),
        ),
        (
            "media_library_reference",
            False,
            "SELECT COUNT(*) FROM web_media_items WHERE asset_id=? AND account_id=?",
            (asset_id, account_id),
        ),
        (
            "image_direction_reference",
            False,
            "SELECT COUNT(*) FROM web_image_directions "
            "WHERE account_id=? AND (asset_id=? OR reference_asset_id=?)",
            (account_id, asset_id, asset_id),
        ),
        (
            "document_plan_reference",
            False,
            "SELECT COUNT(*) FROM web_document_plans "
            "WHERE account_id=? AND (source_asset_id=? OR reference_asset_id=?)",
            (account_id, asset_id, asset_id),
        ),
        (
            "document_operation_source",
            False,
            "SELECT COUNT(*) FROM web_document_operations WHERE source_asset_id=? AND account_id=?",
            (asset_id, account_id),
        ),
        (
            "document_operation_input",
            False,
            "SELECT COUNT(*) FROM web_document_operation_sources AS source "
            "JOIN web_document_operations AS operation ON operation.id=source.operation_id "
            "WHERE source.source_asset_id=? AND operation.account_id=?",
            (asset_id, account_id),
        ),
        (
            "image_operation_source",
            False,
            "SELECT COUNT(*) FROM web_image_operations WHERE source_asset_id=? AND account_id=?",
            (asset_id, account_id),
        ),
        (
            "image_operation_export",
            False,
            """SELECT COUNT(*) FROM web_image_operation_asset_exports
               WHERE asset_id=? AND account_id=? AND state='completed'""",
            (asset_id, account_id),
        ),
        (
            "frame_video_operation_source",
            False,
            "SELECT COUNT(*) FROM web_frame_video_operation_sources AS source "
            "JOIN web_frame_video_operations AS operation ON operation.id=source.operation_id "
            "WHERE source.source_asset_id=? AND operation.account_id=?",
            (asset_id, account_id),
        ),
        (
            "video_transform_operation_source",
            False,
            "SELECT COUNT(*) FROM web_video_transform_operations "
            "WHERE source_asset_id=? AND account_id=?",
            (asset_id, account_id),
        ),
    )
    references: list[dict[str, Any]] = []
    total_count = 0
    hard_blocker_count = 0
    for reason, hard_blocker, query, params in definitions:
        row = conn.execute(query, params).fetchone()
        count = max(0, int(row[0] or 0)) if row else 0
        if not count:
            continue
        total_count += count
        if hard_blocker:
            hard_blocker_count += count
        references.append({"reason": reason, "count": count, "hard_blocker": hard_blocker})
    return {
        "total_count": total_count,
        "hard_blocker_count": hard_blocker_count,
        "references": references,
    }


def _lifecycle_public(row: tuple[Any, ...], *, reference_summary: dict[str, Any]) -> dict[str, Any]:
    state = str(row[7])
    reason_by_state = {
        ACTIVE_STATE: "available",
        ARCHIVED_STATE: "owner_archived",
        UNAVAILABLE_STATE: "integrity_unavailable",
    }
    return {
        "state": state,
        "state_reason": reason_by_state.get(state, "guarded"),
        "lifecycle_revision": _lifecycle_revision(row),
        "created_at": str(row[8]),
        "updated_at": str(row[9]),
        "archived_at": str(row[10]) if row[10] else None,
        "restore_available": state == ARCHIVED_STATE,
        "reference_summary": reference_summary,
    }


def _row_with_lifecycle_state(
    row: tuple[Any, ...],
    *,
    state: str,
    updated_at: str,
    archived_at: str | None,
    lifecycle_revision: int,
) -> tuple[Any, ...]:
    """Create a private-row-shaped value after a bounded lifecycle write."""
    return (*row[:7], state, row[8], updated_at, archived_at, row[11], row[12], lifecycle_revision)


async def _stream_upload(file: UploadFile, destination: Path) -> tuple[int, str, bytes]:
    total = 0
    digest = hashlib.sha256()
    prefix = bytearray()
    limit = _maximum_bytes()
    try:
        with destination.open("xb") as stream:
            while True:
                chunk = await file.read(CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > limit:
                    raise HTTPException(status_code=413, detail="Tệp vượt quá giới hạn Asset Vault")
                if len(prefix) < 64:
                    prefix.extend(chunk[: 64 - len(prefix)])
                digest.update(chunk)
                stream.write(chunk)
    finally:
        await file.close()
    if total == 0:
        raise HTTPException(status_code=422, detail="Tệp không có dữ liệu")
    return total, digest.hexdigest(), bytes(prefix)


def _validate_docx(path: Path) -> None:
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            if not members or len(members) > MAX_DOCX_ARCHIVE_MEMBERS:
                raise HTTPException(status_code=422, detail="DOCX có cấu trúc không an toàn")
            total_uncompressed = 0
            names: set[str] = set()
            for member in members:
                member_name = str(member.filename or "")
                if (
                    not member_name
                    or member_name.startswith("/")
                    or "\\" in member_name
                    or any(part == ".." for part in member_name.split("/"))
                ):
                    raise HTTPException(status_code=422, detail="DOCX có đường dẫn không an toàn")
                total_uncompressed += max(0, int(member.file_size))
                if total_uncompressed > MAX_DOCX_UNCOMPRESSED_BYTES:
                    raise HTTPException(status_code=413, detail="DOCX vượt quá giới hạn giải nén an toàn")
                names.add(member_name)
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise HTTPException(status_code=422, detail="DOCX không có cấu trúc tài liệu hợp lệ")
    except BadZipFile as exc:
        raise HTTPException(status_code=422, detail="DOCX không hợp lệ") from exc


def _validate_text(path: Path) -> None:
    decoder = codecs.getincrementaldecoder("utf-8-sig")()
    has_visible_text = False
    try:
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(CHUNK_BYTES)
                if not chunk:
                    break
                text = decoder.decode(chunk)
                if "\x00" in text:
                    raise HTTPException(status_code=422, detail="Tệp văn bản có dữ liệu không an toàn")
                has_visible_text = has_visible_text or bool(text.strip())
            tail = decoder.decode(b"", final=True)
            if "\x00" in tail:
                raise HTTPException(status_code=422, detail="Tệp văn bản có dữ liệu không an toàn")
            has_visible_text = has_visible_text or bool(tail.strip())
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="Tệp văn bản phải dùng UTF-8") from exc
    if not has_visible_text:
        raise HTTPException(status_code=422, detail="Tệp văn bản không có nội dung")


def _validate_content(path: Path, extension: str, prefix: bytes) -> None:
    if extension == ".pdf":
        valid = prefix.startswith(b"%PDF-")
    elif extension == ".png":
        valid = prefix.startswith(b"\x89PNG\r\n\x1a\n")
    elif extension in {".jpg", ".jpeg"}:
        valid = prefix.startswith(b"\xff\xd8\xff")
    elif extension == ".webp":
        valid = len(prefix) >= 12 and prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP"
    elif extension in {".mp4", ".mov", ".m4a"}:
        valid = len(prefix) >= 12 and prefix[4:8] == b"ftyp"
    elif extension == ".webm":
        valid = prefix.startswith(b"\x1a\x45\xdf\xa3")
    elif extension == ".mp3":
        valid = prefix.startswith(b"ID3") or (len(prefix) >= 2 and prefix[0] == 0xFF and prefix[1] in {0xE2, 0xE3, 0xF2, 0xF3, 0xFA, 0xFB})
    elif extension == ".wav":
        valid = len(prefix) >= 12 and prefix.startswith(b"RIFF") and prefix[8:12] == b"WAVE"
    elif extension == ".ogg":
        valid = prefix.startswith(b"OggS")
    elif extension == ".docx":
        _validate_docx(path)
        return
    elif extension in TEXT_EXTENSIONS:
        _validate_text(path)
        return
    else:
        valid = False
    if not valid:
        raise HTTPException(status_code=422, detail="Nội dung tệp không khớp với định dạng đã chọn")


def _fingerprint(*, file_digest: str, display_name: str, original_filename: str, project_id: str | None) -> str:
    payload = json.dumps(
        {
            "file_digest": file_digest,
            "display_name": display_name,
            "original_filename": original_filename,
            "project_id": project_id or "",
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _pending_marker() -> str:
    return json.dumps({PENDING_MARKER_KEY: uuid.uuid4().hex}, separators=(",", ":"))


def _pending_response(value: str) -> bool:
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return isinstance(decoded, dict) and isinstance(decoded.get(PENDING_MARKER_KEY), str)


def _pending_stale(created_at: str) -> bool:
    try:
        created = datetime.fromisoformat(created_at)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - created > timedelta(seconds=PENDING_SECONDS)
    except (TypeError, ValueError):
        return True


def _reserve_idempotency(scope: str, key: str, fingerprint: str) -> tuple[str, dict[str, Any] | None, str]:
    """Reserve a key before a private blob can be promoted into storage.

    The reservation includes a hash of the intended metadata and content.  A
    reused header key therefore cannot silently create a second asset with
    different input, while an interrupted request can be retried safely.
    """
    ensure_copyfast_schema()
    marker = _pending_marker()
    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            "SELECT response_json, request_fingerprint, created_at FROM web_idempotency WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if row:
            stored, stored_fingerprint, created_at = str(row[0] or ""), str(row[1] or ""), str(row[2] or "")
            if not stored_fingerprint or not hmac.compare_digest(stored_fingerprint, fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho dữ liệu Asset Vault khác")
            if _pending_response(stored):
                if not _pending_stale(created_at):
                    return "pending", None, ""
                conn.execute(
                    """UPDATE web_idempotency
                       SET response_json=?, request_fingerprint=?, created_at=?
                       WHERE scope=? AND key=? AND response_json=?""",
                    (marker, fingerprint, now, scope, key, stored),
                )
                return "owner", None, marker
            try:
                cached = json.loads(stored)
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise HTTPException(status_code=409, detail="Bản ghi idempotency Asset Vault không hợp lệ") from exc
            if isinstance(cached, dict):
                return "cached", cached, ""
            raise HTTPException(status_code=409, detail="Bản ghi idempotency Asset Vault không hợp lệ")
        conn.execute(
            """INSERT INTO web_idempotency (scope, key, response_json, request_fingerprint, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (scope, key, marker, fingerprint, now),
        )
    return "owner", None, marker


def _release_idempotency(scope: str, key: str, marker: str) -> None:
    with transaction() as conn:
        conn.execute(
            "DELETE FROM web_idempotency WHERE scope=? AND key=? AND response_json=?",
            (scope, key, marker),
        )


def _store_response(conn, *, scope: str, key: str, marker: str, fingerprint: str, response: dict[str, Any]) -> None:
    updated = conn.execute(
        """UPDATE web_idempotency SET response_json=?, created_at=?
           WHERE scope=? AND key=? AND response_json=? AND request_fingerprint=?""",
        (json.dumps(response, ensure_ascii=False, separators=(",", ":")), utc_now(), scope, key, marker, fingerprint),
    )
    if updated.rowcount != 1:
        raise RuntimeError("Không thể hoàn tất idempotency Asset Vault")


def _document_operation_export_expected_bytes(value: int) -> int:
    """Accept only a canonical positive byte count supplied by trusted code."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise HTTPException(status_code=422, detail="Kích thước export tài liệu không hợp lệ")
    if value < 1:
        raise HTTPException(status_code=422, detail="Kích thước export tài liệu không hợp lệ")
    if value > _maximum_bytes():
        raise HTTPException(status_code=413, detail="Document export vượt quá giới hạn Asset Vault")
    return value


def _document_operation_export_lease_expiry() -> str:
    return (
        datetime.now(timezone.utc) + timedelta(seconds=DOCUMENT_OPERATION_ASSET_EXPORT_LEASE_SECONDS)
    ).isoformat(timespec="seconds")


def _document_operation_export_lease_is_expired(
    value: str | None,
    *,
    reference_now: datetime | None = None,
) -> bool:
    try:
        expires_at = datetime.fromisoformat(str(value or ""))
        if expires_at.tzinfo is None or (reference_now is not None and reference_now.tzinfo is None):
            return True
        return expires_at <= (reference_now or datetime.now(timezone.utc))
    except (TypeError, ValueError):
        return True


def _document_operation_export_pending_storage_key() -> str:
    return f"objects/{uuid.uuid4().hex}.blob"


def _pending_document_operation_asset_export_bytes(
    conn,
    account_id: str,
    *,
    reference_now: datetime | None = None,
) -> int:
    """Return bytes held by current fenced Document Operation exports."""

    rows = conn.execute(
        """SELECT reserved_bytes, lease_expires_at
           FROM web_document_operation_asset_exports
           WHERE account_id=? AND state='copying' AND lease_token IS NOT NULL""",
        (account_id,),
    ).fetchall()
    return sum(
        max(0, int(row[0] or 0))
        for row in rows
        if not _document_operation_export_lease_is_expired(
            str(row[1] or ""),
            reference_now=reference_now,
        )
    )


def _audio_operation_export_lease_is_expired(value: str | None, *, reference_now: datetime | None = None) -> bool:
    return _document_operation_export_lease_is_expired(value, reference_now=reference_now)


def _audio_operation_export_expected_bytes(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise HTTPException(status_code=422, detail="Kích thước export audio không hợp lệ")
    if value > _maximum_bytes():
        raise HTTPException(status_code=413, detail="Audio export vượt quá giới hạn Asset Vault")
    return value


def _audio_operation_export_lease_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=AUDIO_OPERATION_ASSET_EXPORT_LEASE_SECONDS)).isoformat(timespec="seconds")


def _audio_operation_export_pending_storage_key() -> str:
    return f"objects/{uuid.uuid4().hex}.blob"


def _pending_audio_operation_asset_export_bytes(conn, account_id: str, *, reference_now: datetime | None = None) -> int:
    rows = conn.execute(
        """SELECT reserved_bytes, lease_expires_at FROM web_audio_operation_asset_exports
           WHERE account_id=? AND state='copying' AND lease_token IS NOT NULL""",
        (account_id,),
    ).fetchall()
    return sum(max(0, int(row[0] or 0)) for row in rows if not _audio_operation_export_lease_is_expired(str(row[1] or ""), reference_now=reference_now))


def _cleanup_reclaimed_audio_operation_export_blob(storage_key: object) -> None:
    """Remove only an unreferenced object abandoned by a superseded lease."""

    key = str(storage_key or "")
    if not STORAGE_KEY_PATTERN.fullmatch(key):
        return
    try:
        ensure_copyfast_schema()
        with transaction() as conn:
            referenced = conn.execute(
                "SELECT 1 FROM web_asset_files WHERE storage_key=? LIMIT 1",
                (key,),
            ).fetchone()
        if referenced:
            return
        _safe_unlink(_storage_path(asset_vault_directory(), key))
    except (OSError, RuntimeError):
        # A later bounded Asset Vault reconciliation can retry a failed
        # filesystem cleanup. Never roll back the newly fenced lease for it.
        return


def _pending_image_operation_export_bytes(
    conn,
    account_id: str,
    *,
    reference_now: datetime | None = None,
) -> int:
    """Return bytes held by current fenced exports for one signed account."""

    rows = conn.execute(
        """SELECT reserved_bytes, lease_expires_at
           FROM web_image_operation_asset_exports
           WHERE account_id=? AND state='copying' AND lease_token IS NOT NULL""",
        (account_id,),
    ).fetchall()
    # ``_lease_is_expired`` treats malformed and timezone-naive timestamps as
    # expired.  A damaged/legacy row therefore cannot fail open by retaining
    # a customer's quota indefinitely.
    return sum(
        max(0, int(row[0] or 0))
        for row in rows
        if not _lease_is_expired(str(row[1] or ""), reference_now=reference_now)
    )


def _quota_available(
    conn,
    account_id: str,
    additional_bytes: int,
    *,
    reference_now: datetime | None = None,
) -> bool:
    # Archive deliberately removes download access but does not erase its
    # private blob. Count every retained row so a customer cannot bypass the
    # storage quota by repeatedly upload → archive cycling.
    row = conn.execute(
        "SELECT COALESCE(SUM(byte_size), 0) FROM web_asset_files WHERE account_id=?",
        (account_id,),
    ).fetchone()
    used = int(row[0] or 0) if row else 0
    reserved = (
        _pending_image_operation_export_bytes(conn, account_id, reference_now=reference_now)
        + _pending_document_operation_asset_export_bytes(conn, account_id, reference_now=reference_now)
        + _pending_audio_operation_asset_export_bytes(conn, account_id, reference_now=reference_now)
    )
    return used + reserved + additional_bytes <= _maximum_account_bytes()


def _lease_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=IMAGE_OPERATION_EXPORT_LEASE_SECONDS)).isoformat(
        timespec="seconds"
    )


def _lease_is_expired(
    value: str | None,
    *,
    reference_now: datetime | None = None,
) -> bool:
    try:
        expires_at = datetime.fromisoformat(str(value or ""))
        if expires_at.tzinfo is None or (reference_now is not None and reference_now.tzinfo is None):
            return True
        return expires_at <= (reference_now or datetime.now(timezone.utc))
    except (TypeError, ValueError):
        return True


def _export_pending_storage_key() -> str:
    return f"objects/{uuid.uuid4().hex}.blob"


def _export_lease_from_row(row: tuple[Any, ...]) -> ImageOperationAssetExportLease:
    return ImageOperationAssetExportLease(
        account_id=str(row[1]),
        operation_id=str(row[0]),
        generation=int(row[5]),
        token=str(row[6]),
        expires_at=str(row[7]),
        reserved_bytes=int(row[8]),
        pending_storage_key=str(row[9]),
        request_fingerprint=str(row[4]),
    )


def _insert_export_request_mapping(
    conn,
    *,
    account_id: str,
    idempotency_key: str,
    operation_id: str,
    request_fingerprint: str,
    now: str,
) -> None:
    row = conn.execute(
        """SELECT operation_id, request_fingerprint
           FROM web_image_operation_asset_export_requests
           WHERE account_id=? AND idempotency_key=?""",
        (account_id, idempotency_key),
    ).fetchone()
    if row:
        if str(row[0]) != operation_id or not hmac.compare_digest(str(row[1]), request_fingerprint):
            raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho export khác")
        return
    conn.execute(
        """INSERT INTO web_image_operation_asset_export_requests
           (account_id, idempotency_key, operation_id, request_fingerprint, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (account_id, idempotency_key, operation_id, request_fingerprint, now, now),
    )


def reserve_image_operation_asset_export(
    *,
    account_id: str,
    operation_id: str,
    idempotency_key: str,
    request_fingerprint: str,
    expected_bytes: int,
) -> ImageOperationAssetExportReservation:
    """Reserve exactly one private-object attempt for an Image Operation.

    This writes only the fenced intent. It deliberately does not copy a byte,
    open an Image Operation path, or create Asset Vault metadata; callers must
    finish through a matching current lease.
    """

    _require_image_operation_export_enabled()
    scoped_account_id = _validate_id(account_id, label="Web account ID")
    scoped_operation_id = _image_operation_id(operation_id)
    key = _idempotency_key(idempotency_key)
    fingerprint = _export_request_fingerprint(request_fingerprint)
    byte_size = int(expected_bytes)
    if byte_size < 1 or byte_size > _maximum_bytes():
        raise HTTPException(status_code=413, detail="PNG export vượt quá giới hạn Asset Vault")
    ensure_copyfast_schema()
    now = utc_now()
    with transaction() as conn:
        operation = conn.execute(
            "SELECT state FROM web_image_operations WHERE id=? AND account_id=?",
            (scoped_operation_id, scoped_account_id),
        ).fetchone()
        if not operation:
            raise HTTPException(status_code=404, detail="Không tìm thấy thao tác ảnh thuộc Web account hiện tại")
        if str(operation[0]) != "completed":
            raise HTTPException(status_code=409, detail="PNG Image Operation chưa sẵn sàng để lưu")
        relation = conn.execute(
            """SELECT operation_id, account_id, asset_id, state, request_fingerprint,
                      lease_generation, lease_token, lease_expires_at, reserved_bytes,
                      pending_storage_key, created_at, updated_at, completed_at
               FROM web_image_operation_asset_exports
               WHERE operation_id=? AND account_id=?""",
            (scoped_operation_id, scoped_account_id),
        ).fetchone()
        if relation:
            if not hmac.compare_digest(str(relation[4]), fingerprint):
                raise HTTPException(status_code=409, detail="Export này không còn khớp output đã xác minh")
            state = str(relation[3])
            _insert_export_request_mapping(
                conn,
                account_id=scoped_account_id,
                idempotency_key=key,
                operation_id=scoped_operation_id,
                request_fingerprint=fingerprint,
                now=now,
            )
            if state == "completed":
                return ImageOperationAssetExportReservation(state="completed")
            if state != "copying" or not _lease_is_expired(str(relation[7] or "")):
                return ImageOperationAssetExportReservation(state="pending")
            # An expired row no longer consumes quota. Recheck before making
            # it live again, because a separate image/document lease may have
            # claimed that capacity while this worker was stale.
            if not _quota_available(conn, scoped_account_id, int(relation[8])):
                raise HTTPException(status_code=413, detail="Asset Vault đã đạt quota của Web account")
            previous_generation = int(relation[5])
            next_generation = previous_generation + 1
            token = uuid.uuid4().hex
            expires_at = _lease_expiry()
            pending_storage_key = _export_pending_storage_key()
            updated = conn.execute(
                """UPDATE web_image_operation_asset_exports
                   SET lease_generation=?, lease_token=?, lease_expires_at=?,
                       pending_storage_key=?, updated_at=?
                   WHERE operation_id=? AND account_id=? AND state='copying'
                     AND lease_generation=? AND lease_token=? AND lease_expires_at=?""",
                (
                    next_generation,
                    token,
                    expires_at,
                    pending_storage_key,
                    now,
                    scoped_operation_id,
                    scoped_account_id,
                    previous_generation,
                    relation[6],
                    relation[7],
                ),
            )
            if updated.rowcount != 1:
                return ImageOperationAssetExportReservation(state="pending")
            return ImageOperationAssetExportReservation(
                state="leased",
                lease=ImageOperationAssetExportLease(
                    account_id=scoped_account_id,
                    operation_id=scoped_operation_id,
                    generation=next_generation,
                    token=token,
                    expires_at=expires_at,
                    pending_storage_key=pending_storage_key,
                    reserved_bytes=int(relation[8]),
                    request_fingerprint=fingerprint,
                ),
            )
        if not _quota_available(conn, scoped_account_id, byte_size):
            raise HTTPException(status_code=413, detail="Asset Vault đã đạt quota của Web account")
        token = uuid.uuid4().hex
        expires_at = _lease_expiry()
        pending_storage_key = _export_pending_storage_key()
        conn.execute(
            """INSERT INTO web_image_operation_asset_exports
               (operation_id, account_id, asset_id, state, request_fingerprint,
                lease_generation, lease_token, lease_expires_at, reserved_bytes,
                pending_storage_key, created_at, updated_at, completed_at)
               VALUES (?, ?, NULL, 'copying', ?, 1, ?, ?, ?, ?, ?, ?, NULL)""",
            (
                scoped_operation_id,
                scoped_account_id,
                fingerprint,
                token,
                expires_at,
                byte_size,
                pending_storage_key,
                now,
                now,
            ),
        )
        _insert_export_request_mapping(
            conn,
            account_id=scoped_account_id,
            idempotency_key=key,
            operation_id=scoped_operation_id,
            request_fingerprint=fingerprint,
            now=now,
        )
    return ImageOperationAssetExportReservation(
        state="leased",
        lease=ImageOperationAssetExportLease(
            account_id=scoped_account_id,
            operation_id=scoped_operation_id,
            generation=1,
            token=token,
            expires_at=expires_at,
            pending_storage_key=pending_storage_key,
            reserved_bytes=byte_size,
            request_fingerprint=fingerprint,
        ),
    )


def release_image_operation_asset_export_lease(lease: ImageOperationAssetExportLease) -> bool:
    """Release only the caller's live fenced lease; a stale worker is a no-op."""

    ensure_copyfast_schema()
    now = utc_now()
    with transaction() as conn:
        current = conn.execute(
            """SELECT 1 FROM web_image_operation_asset_exports
               WHERE operation_id=? AND account_id=? AND state='copying'
                 AND lease_generation=? AND lease_token=? AND lease_expires_at=?
                 AND lease_expires_at > ?""",
            (
                lease.operation_id,
                lease.account_id,
                lease.generation,
                lease.token,
                lease.expires_at,
                now,
            ),
        ).fetchone()
        if not current:
            return False
        # The request map is a child of the export relation.  Delete it only
        # after proving this exact lease is still live, then delete the parent
        # under the same fence in the same writer transaction.
        conn.execute(
            "DELETE FROM web_image_operation_asset_export_requests WHERE operation_id=? AND account_id=?",
            (lease.operation_id, lease.account_id),
        )
        removed = conn.execute(
            """DELETE FROM web_image_operation_asset_exports
               WHERE operation_id=? AND account_id=? AND state='copying'
                 AND lease_generation=? AND lease_token=? AND lease_expires_at=?
                 AND lease_expires_at > ?""",
            (
                lease.operation_id,
                lease.account_id,
                lease.generation,
                lease.token,
                lease.expires_at,
                now,
            ),
        )
        if removed.rowcount != 1:
            raise RuntimeError("Không thể giải phóng export lease hiện tại")
    return True


def _copy_image_operation_export_source(source: ImageOperationAssetExportSource, destination: Path) -> tuple[int, str]:
    """Boundedly copy the pinned source stream into Vault staging and rehash it."""

    digest = hashlib.sha256()
    copied = 0
    try:
        source.stream.seek(0)
        with destination.open("xb") as staged:
            while True:
                chunk = source.stream.read(CHUNK_BYTES)
                if not chunk:
                    break
                copied += len(chunk)
                if copied > source.byte_size or copied > _maximum_bytes():
                    raise RuntimeError("PNG Image Operation vượt giới hạn Asset Vault")
                digest.update(chunk)
                staged.write(chunk)
            staged.flush()
            os.fsync(staged.fileno())
    except Exception:
        _safe_unlink(destination)
        raise
    if copied != source.byte_size or not hmac.compare_digest(digest.hexdigest(), source.sha256):
        _safe_unlink(destination)
        raise RuntimeError("PNG Image Operation không còn integrity")
    return copied, digest.hexdigest()


def _promote_image_operation_export_staging(staging: Path, destination: Path) -> None:
    """Create the attempt-owned Vault object without replacing any existing file."""

    try:
        # A hard link gives same-filesystem staging an exclusive destination
        # creation primitive: unlike ``replace``, it cannot overwrite a newer
        # fenced attempt or an unexpected object at this random key.
        os.link(staging, destination, follow_symlinks=False)
    except FileExistsError as exc:
        raise RuntimeError("Khóa lưu PNG Image Operation không còn độc quyền") from exc
    except OSError as exc:
        raise RuntimeError("Không thể tạo vùng lưu Asset Vault riêng tư") from exc
    finally:
        _safe_unlink(staging)


def _image_operation_export_png_contract(source: ImageOperationAssetExportSource) -> tuple[int, int, str, bool] | None:
    """Derive the exact destination PNG rules from an allow-listed source.

    The finalizer receives a descriptor-pinned source from Image Operations,
    but its own private object must still be parsed independently.  Keep the
    derived contract local to the narrow export boundary instead of accepting
    a caller-provided MIME/mode/dimension assertion.
    """

    if source.kind not in IMAGE_OPERATION_EXPORT_KINDS:
        return None
    if isinstance(source.width, bool) or isinstance(source.height, bool):
        return None
    try:
        width = int(source.width)
        height = int(source.height)
    except (TypeError, ValueError):
        return None
    if width < 1 or height < 1:
        return None
    is_background_cleanup = source.kind == "image_background_cleanup"
    return width, height, "RGBA" if is_background_cleanup else "RGB", is_background_cleanup


def _png_stream_has_no_exif_chunk(stream: BinaryIO) -> bool:
    """Reject a PNG eXIf chunk even when Pillow exposes an empty EXIF map."""

    signature = b"\x89PNG\r\n\x1a\n"
    try:
        stream.seek(0)
        if stream.read(len(signature)) != signature:
            return False
        while True:
            header = stream.read(8)
            if len(header) != 8:
                return False
            payload_size = int.from_bytes(header[:4], byteorder="big", signed=False)
            chunk_type = header[4:]
            if chunk_type == b"eXIf":
                return False
            remaining = payload_size
            while remaining:
                chunk = stream.read(min(CHUNK_BYTES, remaining))
                if not chunk:
                    return False
                remaining -= len(chunk)
            if len(stream.read(4)) != 4:
                return False
            if chunk_type == b"IEND":
                return not bool(stream.read(1))
    except (OSError, ValueError):
        return False
    finally:
        try:
            stream.seek(0)
        except (OSError, ValueError):
            pass


def _verify_image_operation_export_destination_png(
    path: Path,
    *,
    expected_bytes: int,
    expected_digest: str,
    source: ImageOperationAssetExportSource,
) -> bool:
    """Parse the final pinned Vault object against the Image Operation contract.

    Hash/size equality proves copied bytes, but it cannot establish that those
    bytes are a complete, static PNG with the allowed pixel mode.  Open the
    promoted final object exactly once through the descriptor-pinned Asset
    Vault reader, verify/decode it, then rehash that same descriptor before
    metadata can be committed.
    """

    contract = _image_operation_export_png_contract(source)
    if contract is None:
        return False
    expected_width, expected_height, expected_mode, require_transparent_pixel = contract
    stream = _open_verified_private_file(
        path,
        expected_bytes=expected_bytes,
        expected_digest=expected_digest,
    )
    if stream is None:
        return False
    try:
        if not _png_stream_has_no_exif_chunk(stream):
            return False
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            stream.seek(0)
            with Image.open(stream) as verifier:
                # Pillow requires this as the first parser action.
                verifier.verify()
            stream.seek(0)
            with Image.open(stream) as decoded:
                if str(decoded.format or "").upper() != "PNG":
                    return False
                if int(getattr(decoded, "n_frames", 1) or 1) != 1 or bool(getattr(decoded, "is_animated", False)):
                    return False
                if tuple(decoded.size) != (expected_width, expected_height):
                    return False
                if str(decoded.mode or "") != expected_mode:
                    return False
                if decoded.getexif():
                    return False
                decoded.load()
                if require_transparent_pixel:
                    alpha = decoded.getchannel("A")
                    try:
                        extrema = alpha.getextrema()
                    finally:
                        alpha.close()
                    if not extrema or int(extrema[0]) >= 255:
                        return False
        return _verify_pinned_private_file(
            stream,
            expected_bytes=expected_bytes,
            expected_digest=expected_digest,
        )
    except (
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        return False
    finally:
        stream.close()


def finalize_image_operation_asset_export(
    *,
    lease: ImageOperationAssetExportLease,
    source: ImageOperationAssetExportSource,
    request_id: str,
) -> ImageOperationAssetExportFinalization:
    """Finalize one current fenced source copy as an independent private asset.

    This function owns the source descriptor after entry and always closes it.
    Source verification is deliberately performed by the Image Operations
    boundary before constructing ``source``; this persistence half rehashes
    the stream and the promoted Vault object before committing any metadata.
    """

    _require_image_operation_export_enabled()
    final_path: Path | None = None
    staging: Path | None = None
    completed = False
    try:
        if (
            source.account_id != lease.account_id
            or source.operation_id != lease.operation_id
            or source.kind not in IMAGE_OPERATION_EXPORT_KINDS
            or source.byte_size < 1
            or source.byte_size != lease.reserved_bytes
            or source.byte_size > _maximum_bytes()
            or not hmac.compare_digest(_export_request_fingerprint(source.sha256), lease.request_fingerprint)
        ):
            raise RuntimeError("Nguồn PNG Image Operation không khớp export lease")
        original_filename, extension = _safe_filename(source.original_filename)
        if extension != ".png":
            raise RuntimeError("Nguồn Image Operation không phải PNG hợp lệ")

        root = asset_vault_directory()
        staging = _staging_path(root)
        copied_bytes, copied_digest = _copy_image_operation_export_source(source, staging)
        final_path = _storage_path(root, lease.pending_storage_key)
        _private_asset_vault_child_directory(root, "objects")
        _promote_image_operation_export_staging(staging, final_path)
        staging = None
        if not _verify_image_operation_export_destination_png(
            final_path,
            expected_bytes=copied_bytes,
            expected_digest=copied_digest,
            source=source,
        ):
            raise RuntimeError("PNG đã sao chép không vượt qua kiểm tra Asset Vault")

        now = utc_now()
        asset_id = str(uuid.uuid4())
        resolved_project_id: str | None = None
        with transaction() as conn:
            if source.project_id:
                project = conn.execute(
                    "SELECT id FROM web_projects WHERE id=? AND account_id=? AND state='active'",
                    (source.project_id, lease.account_id),
                ).fetchone()
                if project:
                    resolved_project_id = str(project[0])
            if not _quota_available(conn, lease.account_id, 0):
                raise HTTPException(status_code=413, detail="Asset Vault đã đạt quota của Web account")
            conn.execute(
                """INSERT INTO web_asset_files
                   (id, account_id, project_id, display_name, original_filename, extension, content_type,
                    byte_size, sha256, storage_key, state, created_at, updated_at, archived_at)
                   VALUES (?, ?, ?, ?, ?, '.png', 'image/png', ?, ?, ?, 'active', ?, ?, NULL)""",
                (
                    asset_id,
                    lease.account_id,
                    resolved_project_id,
                    f"Bản sao {original_filename}",
                    original_filename,
                    copied_bytes,
                    copied_digest,
                    lease.pending_storage_key,
                    now,
                    now,
                ),
            )
            updated = conn.execute(
                """UPDATE web_image_operation_asset_exports
                   SET asset_id=?, state='completed', lease_token=NULL, lease_expires_at=NULL,
                       reserved_bytes=0, pending_storage_key=NULL, completed_at=?, updated_at=?
                   WHERE operation_id=? AND account_id=? AND state='copying'
                     AND request_fingerprint=? AND lease_generation=? AND lease_token=?
                     AND lease_expires_at=? AND lease_expires_at > ? AND asset_id IS NULL""",
                (
                    asset_id,
                    now,
                    now,
                    lease.operation_id,
                    lease.account_id,
                    lease.request_fingerprint,
                    lease.generation,
                    lease.token,
                    lease.expires_at,
                    now,
                ),
            )
            if updated.rowcount != 1:
                raise RuntimeError("Export lease không còn hiện tại khi hoàn tất Asset Vault")
            _record_audit(
                conn,
                account_id=lease.account_id,
                canonical_user_id=None,
                action="web.image_operation.export_to_asset_vault",
                request_id=str(request_id or "")[:160],
                target=asset_id,
                detail=f"kind={source.kind};bytes={copied_bytes}",
            )
        completed = True
        return ImageOperationAssetExportFinalization(
            state="completed",
            asset={
                "id": asset_id,
                "project_id": resolved_project_id,
                "display_name": f"Bản sao {original_filename}",
                "original_filename": original_filename,
                "extension": ".png",
                "content_type": "image/png",
                "byte_size": copied_bytes,
                "state": ACTIVE_STATE,
                "created_at": now,
                "updated_at": now,
                "archived_at": None,
            },
        )
    finally:
        try:
            source.stream.close()
        except OSError:
            pass
        _safe_unlink(staging) if staging is not None else None
        if not completed:
            _safe_unlink(final_path)


def get_image_operation_asset_export_receipt(
    *,
    account_id: str,
    operation_id: str,
) -> ImageOperationAssetExportFinalization | None:
    """Read the relation and its Asset Vault lifecycle at response time.

    This intentionally does not consult ``web_idempotency``.  A replay must
    describe the independent asset as it exists now (including archived or
    unavailable), never return an old serialized success snapshot.
    """

    _require_image_operation_export_enabled()
    scoped_account_id = _validate_id(account_id, label="Web account ID")
    scoped_operation_id = _image_operation_id(operation_id)
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            """SELECT export.state, export.asset_id,
                      asset.id, asset.project_id, asset.display_name, asset.original_filename,
                      asset.extension, asset.content_type, asset.byte_size, asset.state,
                      asset.created_at, asset.updated_at, asset.archived_at
               FROM web_image_operation_asset_exports AS export
               LEFT JOIN web_asset_files AS asset
                 ON asset.id=export.asset_id AND asset.account_id=export.account_id
               WHERE export.operation_id=? AND export.account_id=?""",
            (scoped_operation_id, scoped_account_id),
        ).fetchone()
    if not row:
        return None
    relation_state = str(row[0] or "")
    if relation_state != "completed":
        return ImageOperationAssetExportFinalization(state=relation_state or "guarded", asset=None)
    if not row[1] or not row[2]:
        return ImageOperationAssetExportFinalization(state="guarded", asset=None)
    return ImageOperationAssetExportFinalization(
        state="completed",
        asset=_asset_public(tuple(row[2:])),
    )


def replay_image_operation_asset_export(
    *,
    account_id: str,
    operation_id: str,
    idempotency_key: str,
) -> ImageOperationAssetExportFinalization | None:
    """Join an existing export lifecycle and bind a fresh opaque replay key."""

    _require_image_operation_export_enabled()
    scoped_account_id = _validate_id(account_id, label="Web account ID")
    scoped_operation_id = _image_operation_id(operation_id)
    key = _idempotency_key(idempotency_key)
    ensure_copyfast_schema()
    now = utc_now()
    with transaction() as conn:
        relation = conn.execute(
            """SELECT request_fingerprint, state, lease_expires_at
               FROM web_image_operation_asset_exports
               WHERE operation_id=? AND account_id=?""",
            (scoped_operation_id, scoped_account_id),
        ).fetchone()
        if not relation:
            return None
        # A copying relation whose fence has expired is not a live replay.
        # Return control to the reservation path so its CAS reclaim can mint a
        # new generation.  Binding a replay key here would otherwise leave the
        # endpoint permanently reporting ``processing`` without ever reaching
        # the reclaim logic.
        if str(relation[1] or "") == "copying" and _lease_is_expired(str(relation[2] or "")):
            return None
        _insert_export_request_mapping(
            conn,
            account_id=scoped_account_id,
            idempotency_key=key,
            operation_id=scoped_operation_id,
            request_fingerprint=str(relation[0]),
            now=now,
        )
    return get_image_operation_asset_export_receipt(
        account_id=scoped_account_id,
        operation_id=scoped_operation_id,
    )


def _document_operation_export_lease_from_row(row: tuple[Any, ...]) -> DocumentOperationAssetExportLease:
    return DocumentOperationAssetExportLease(
        account_id=str(row[1]),
        operation_id=str(row[0]),
        generation=int(row[5]),
        token=str(row[6]),
        expires_at=str(row[7]),
        reserved_bytes=int(row[8]),
        pending_storage_key=str(row[9]),
        request_fingerprint=str(row[4]),
    )


def _insert_document_operation_asset_export_request_mapping(
    conn,
    *,
    account_id: str,
    idempotency_key: str,
    operation_id: str,
    request_fingerprint: str,
    now: str,
) -> None:
    row = conn.execute(
        """SELECT operation_id, request_fingerprint
           FROM web_document_operation_asset_export_requests
           WHERE account_id=? AND idempotency_key=?""",
        (account_id, idempotency_key),
    ).fetchone()
    if row:
        if str(row[0]) != operation_id or not hmac.compare_digest(str(row[1]), request_fingerprint):
            raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho document export khác")
        return
    conn.execute(
        """INSERT INTO web_document_operation_asset_export_requests
           (account_id, idempotency_key, operation_id, request_fingerprint, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (account_id, idempotency_key, operation_id, request_fingerprint, now, now),
    )


def _completed_document_operation_asset_export_snapshot_is_valid(
    conn,
    *,
    account_id: str,
    operation_id: str,
    asset_id: object,
    export_fingerprint: object,
) -> bool:
    """Return whether a completed export still exactly matches its sealed spec."""

    row = conn.execute(
        """SELECT operation.kind, operation.sha256, operation.byte_size,
                  asset.extension, asset.content_type, asset.original_filename,
                  asset.storage_key, asset.byte_size, asset.sha256, asset.state
           FROM web_document_operations AS operation
           JOIN web_asset_files AS asset
             ON asset.id=? AND asset.account_id=operation.account_id
           WHERE operation.id=? AND operation.account_id=?""",
        (asset_id, operation_id, account_id),
    ).fetchone()
    if not row:
        return False
    expected_spec = DOCUMENT_OPERATION_ASSET_EXPORT_SPECS.get(str(row[0] or ""))
    if expected_spec is None or str(row[9] or "") != ACTIVE_STATE:
        return False
    expected_extension, expected_content_type, expected_original_filename = expected_spec
    if (
        str(row[3] or "") != expected_extension
        or str(row[4] or "") != expected_content_type
        or str(row[5] or "") != expected_original_filename
        or not STORAGE_KEY_PATTERN.fullmatch(str(row[6] or ""))
    ):
        return False
    normalized_fingerprints = tuple(
        str(value or "").strip().lower()
        for value in (export_fingerprint, row[1], row[8])
    )
    if not all(re.fullmatch(r"[0-9a-f]{64}", value) for value in normalized_fingerprints):
        return False
    try:
        operation_byte_size = int(row[2])
        asset_byte_size = int(row[7])
    except (TypeError, ValueError):
        return False
    return (
        operation_byte_size > 0
        and operation_byte_size == asset_byte_size
        and all(
            hmac.compare_digest(normalized_fingerprints[0], value)
            for value in normalized_fingerprints[1:]
        )
    )


def reserve_document_operation_asset_export(
    *,
    account_id: str,
    operation_id: str,
    idempotency_key: str,
    request_fingerprint: str,
    expected_bytes: int,
) -> DocumentOperationAssetExportReservation:
    """Reserve one fenced private-object attempt for a completed Document Operation.

    This records only immutable, owner-scoped intent.  It deliberately does
    not open a document output, write a filesystem blob, or create an Asset
    Vault row; a later document-specific finalizer must hold this exact lease.
    """

    _require_document_operation_asset_export_enabled()
    scoped_account_id = _validate_id(account_id, label="Web account ID")
    scoped_operation_id = _document_operation_id(operation_id)
    key = _idempotency_key(idempotency_key)
    fingerprint = _export_request_fingerprint(request_fingerprint)
    byte_size = _document_operation_export_expected_bytes(expected_bytes)
    ensure_copyfast_schema()
    now = utc_now()
    with transaction() as conn:
        operation = conn.execute(
            "SELECT state, sha256, byte_size FROM web_document_operations WHERE id=? AND account_id=?",
            (scoped_operation_id, scoped_account_id),
        ).fetchone()
        if not operation:
            raise HTTPException(status_code=404, detail="Không tìm thấy thao tác tài liệu thuộc Web account hiện tại")
        if str(operation[0]) != "completed":
            raise HTTPException(status_code=409, detail="Document Operation chưa sẵn sàng để lưu")
        if not hmac.compare_digest(str(operation[1] or ""), fingerprint):
            raise HTTPException(status_code=409, detail="Document export này không còn khớp output đã xác minh")
        try:
            operation_bytes = int(operation[2])
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=409, detail="Bản ghi Document Operation không hợp lệ") from exc
        if operation_bytes != byte_size:
            raise HTTPException(status_code=409, detail="Document export này không còn khớp kích thước đã xác minh")
        relation = conn.execute(
            """SELECT operation_id, account_id, asset_id, state, request_fingerprint,
                      lease_generation, lease_token, lease_expires_at, reserved_bytes,
                      pending_storage_key, created_at, updated_at, completed_at
               FROM web_document_operation_asset_exports
               WHERE operation_id=? AND account_id=?""",
            (scoped_operation_id, scoped_account_id),
        ).fetchone()
        if relation:
            if not hmac.compare_digest(str(relation[4]), fingerprint):
                raise HTTPException(status_code=409, detail="Document export này không còn khớp output đã xác minh")
            state = str(relation[3])
            # A completed relation intentionally clears its transient lease
            # reservation to zero.  Its independent Asset Vault row retains
            # the output byte count, so preserve the size fence there without
            # comparing a later source to the cleared transient field.
            if state == "completed":
                if not _completed_document_operation_asset_export_snapshot_is_valid(
                    conn,
                    account_id=scoped_account_id,
                    operation_id=scoped_operation_id,
                    asset_id=relation[2],
                    export_fingerprint=relation[4],
                ):
                    return DocumentOperationAssetExportReservation(state="guarded")
                _insert_document_operation_asset_export_request_mapping(
                    conn,
                    account_id=scoped_account_id,
                    idempotency_key=key,
                    operation_id=scoped_operation_id,
                    request_fingerprint=fingerprint,
                    now=now,
                )
                return DocumentOperationAssetExportReservation(state="completed")
            try:
                reserved_bytes = int(relation[8])
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=409, detail="Bản ghi document export không hợp lệ") from exc
            if reserved_bytes != byte_size:
                raise HTTPException(status_code=409, detail="Document export này không còn khớp kích thước đã xác minh")
            _insert_document_operation_asset_export_request_mapping(
                conn,
                account_id=scoped_account_id,
                idempotency_key=key,
                operation_id=scoped_operation_id,
                request_fingerprint=fingerprint,
                now=now,
            )
            if state != "copying" or not _document_operation_export_lease_is_expired(str(relation[7] or "")):
                return DocumentOperationAssetExportReservation(state="pending")
            # An expired row no longer consumes quota.  Recheck before making
            # it live again, because a separate image/document lease may have
            # claimed that capacity while this worker was stale.
            if not _quota_available(conn, scoped_account_id, reserved_bytes):
                raise HTTPException(status_code=413, detail="Asset Vault đã đạt quota của Web account")
            previous_generation = int(relation[5])
            next_generation = previous_generation + 1
            token = uuid.uuid4().hex
            expires_at = _document_operation_export_lease_expiry()
            pending_storage_key = _document_operation_export_pending_storage_key()
            updated = conn.execute(
                """UPDATE web_document_operation_asset_exports
                   SET lease_generation=?, lease_token=?, lease_expires_at=?,
                       pending_storage_key=?, updated_at=?
                   WHERE operation_id=? AND account_id=? AND state='copying'
                     AND lease_generation=? AND lease_token=? AND lease_expires_at=?""",
                (
                    next_generation,
                    token,
                    expires_at,
                    pending_storage_key,
                    now,
                    scoped_operation_id,
                    scoped_account_id,
                    previous_generation,
                    relation[6],
                    relation[7],
                ),
            )
            if updated.rowcount != 1:
                return DocumentOperationAssetExportReservation(state="pending")
            return DocumentOperationAssetExportReservation(
                state="leased",
                lease=DocumentOperationAssetExportLease(
                    account_id=scoped_account_id,
                    operation_id=scoped_operation_id,
                    generation=next_generation,
                    token=token,
                    expires_at=expires_at,
                    pending_storage_key=pending_storage_key,
                    reserved_bytes=reserved_bytes,
                    request_fingerprint=fingerprint,
                ),
            )
        if not _quota_available(conn, scoped_account_id, byte_size):
            raise HTTPException(status_code=413, detail="Asset Vault đã đạt quota của Web account")
        token = uuid.uuid4().hex
        expires_at = _document_operation_export_lease_expiry()
        pending_storage_key = _document_operation_export_pending_storage_key()
        conn.execute(
            """INSERT INTO web_document_operation_asset_exports
               (operation_id, account_id, asset_id, state, request_fingerprint,
                lease_generation, lease_token, lease_expires_at, reserved_bytes,
                pending_storage_key, created_at, updated_at, completed_at)
               VALUES (?, ?, NULL, 'copying', ?, 1, ?, ?, ?, ?, ?, ?, NULL)""",
            (
                scoped_operation_id,
                scoped_account_id,
                fingerprint,
                token,
                expires_at,
                byte_size,
                pending_storage_key,
                now,
                now,
            ),
        )
        _insert_document_operation_asset_export_request_mapping(
            conn,
            account_id=scoped_account_id,
            idempotency_key=key,
            operation_id=scoped_operation_id,
            request_fingerprint=fingerprint,
            now=now,
        )
    return DocumentOperationAssetExportReservation(
        state="leased",
        lease=DocumentOperationAssetExportLease(
            account_id=scoped_account_id,
            operation_id=scoped_operation_id,
            generation=1,
            token=token,
            expires_at=expires_at,
            pending_storage_key=pending_storage_key,
            reserved_bytes=byte_size,
            request_fingerprint=fingerprint,
        ),
    )


def release_document_operation_asset_export_lease(lease: DocumentOperationAssetExportLease) -> bool:
    """Release only the caller's current Document Operation export lease."""

    ensure_copyfast_schema()
    now = utc_now()
    with transaction() as conn:
        released = conn.execute(
            """UPDATE web_document_operation_asset_exports
               SET lease_expires_at=?, updated_at=?
               WHERE operation_id=? AND account_id=? AND state='copying'
                 AND lease_generation=? AND lease_token=? AND lease_expires_at=?
                 AND lease_expires_at > ?""",
            (
                now,
                now,
                lease.operation_id,
                lease.account_id,
                lease.generation,
                lease.token,
                lease.expires_at,
                now,
            ),
        )
        if released.rowcount != 1:
            return False
    return True


def _copy_document_operation_asset_export_source(
    source: DocumentOperationAssetExportSource,
    destination: Path,
) -> tuple[int, str]:
    """Boundedly copy and rehash the already-pinned Document Operation stream."""

    digest = hashlib.sha256()
    copied = 0
    try:
        source.stream.seek(0)
        with destination.open("xb") as staged:
            while True:
                chunk = source.stream.read(CHUNK_BYTES)
                if not chunk:
                    break
                copied += len(chunk)
                if copied > source.byte_size or copied > _maximum_bytes():
                    raise RuntimeError("Document Operation vượt giới hạn Asset Vault")
                digest.update(chunk)
                staged.write(chunk)
            staged.flush()
            os.fsync(staged.fileno())
    except Exception:
        _safe_unlink(destination)
        raise
    if copied != source.byte_size or not hmac.compare_digest(digest.hexdigest(), source.sha256):
        _safe_unlink(destination)
        raise RuntimeError("Document Operation không còn integrity")
    return copied, digest.hexdigest()


def _verify_document_operation_asset_export_destination_pdf(
    path: Path,
    *,
    expected_bytes: int,
    expected_digest: str,
) -> bool:
    """Strictly parse and rehash the promoted PDF on one pinned descriptor."""

    stream = _open_verified_private_file(
        path,
        expected_bytes=expected_bytes,
        expected_digest=expected_digest,
    )
    if stream is None:
        return False
    try:
        if not _pdf_has_terminal_eof(stream, expected_bytes=expected_bytes):
            return False
        reader = PdfReader(stream, strict=True)
        if reader.is_encrypted or len(reader.pages) < 1:
            return False
        # Rehash after pypdf consumed the descriptor; this confirms the same
        # pinned file still has the exact accepted bytes at finalization time.
        return _verify_pinned_private_file(
            stream,
            expected_bytes=expected_bytes,
            expected_digest=expected_digest,
        )
    except Exception:
        return False
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _document_operation_docx_member_name_is_safe(name: str) -> bool:
    """Keep DOCX ZIP members strictly relative, normalized and file-shaped."""

    if not name or "\x00" in name or name.startswith("/") or "\\" in name:
        return False
    parts = name.split("/")
    return all(
        part and part not in {".", ".."} and ":" not in part
        for part in parts
    )


def _document_operation_docx_safe_xml_root(payload: bytes):
    """Decode XML as strict UTF-8 data and reject active declaration syntax."""

    try:
        if not isinstance(payload, bytes):
            return None
        text = payload.decode("utf-8-sig", errors="strict")
        if "\x00" in text or re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, flags=re.IGNORECASE):
            return None
        return ElementTree.fromstring(text)
    except (ElementTree.ParseError, TypeError, UnicodeDecodeError, ValueError):
        return None


def _document_operation_docx_relationships_are_safe(payload: bytes) -> bool:
    """Reject relationship parts that can make a DOCX dereference a URL."""

    root = _document_operation_docx_safe_xml_root(payload)
    relationships_tag = f"{{{DOCX_RELATIONSHIPS_NAMESPACE}}}Relationships"
    relationship_tag = f"{{{DOCX_RELATIONSHIPS_NAMESPACE}}}Relationship"
    if root is None or root.tag != relationships_tag:
        return False
    for relationship in root.iter(relationship_tag):
        if str(relationship.attrib.get("TargetMode", "")).strip().casefold() == "external":
            return False
    return True


def _document_operation_docx_package_relationships_are_valid(payload: bytes) -> bool:
    """Require one internal package-root relationship to the main Word part."""

    root = _document_operation_docx_safe_xml_root(payload)
    relationships_tag = f"{{{DOCX_RELATIONSHIPS_NAMESPACE}}}Relationships"
    relationship_tag = f"{{{DOCX_RELATIONSHIPS_NAMESPACE}}}Relationship"
    if root is None or root.tag != relationships_tag:
        return False
    office_documents = []
    relationship_ids: set[str] = set()
    for relationship in root:
        if relationship.tag != relationship_tag:
            return False
        relationship_id = relationship.attrib.get("Id", "")
        if (
            not relationship_id
            or relationship_id in relationship_ids
            or any(
                character.isspace() or unicodedata.category(character) == "Cc"
                for character in relationship_id
            )
        ):
            return False
        relationship_ids.add(relationship_id)
        if relationship.attrib.get("Type") == DOCX_OFFICE_DOCUMENT_RELATIONSHIP:
            office_documents.append(relationship)
    if len(office_documents) != 1:
        return False
    relationship = office_documents[0]
    return (
        str(relationship.attrib.get("TargetMode", "")).strip().casefold() in {"", "internal"}
        and relationship.attrib.get("Target") == "word/document.xml"
    )


def _document_operation_docx_required_xml_is_valid(payload: bytes, *, expected_tag: str) -> bool:
    """Require one required OOXML part to be parseable with its exact root."""

    root = _document_operation_docx_safe_xml_root(payload)
    return root is not None and root.tag == expected_tag


def _document_operation_docx_content_types_are_valid(payload: bytes) -> bool:
    """Require the canonical content-type override for the main Word part."""

    root = _document_operation_docx_safe_xml_root(payload)
    types_tag = f"{{{DOCX_CONTENT_TYPES_NAMESPACE}}}Types"
    override_tag = f"{{{DOCX_CONTENT_TYPES_NAMESPACE}}}Override"
    if root is None or root.tag != types_tag:
        return False
    document_overrides = [
        override
        for override in root.findall(override_tag)
        if override.attrib.get("PartName") == "/word/document.xml"
    ]
    return (
        len(document_overrides) == 1
        and document_overrides[0].attrib.get("ContentType") == DOCX_WORD_MAIN_CONTENT_TYPE
    )


def _document_operation_docx_has_safe_classic_eocd(stream: BinaryIO) -> bool:
    """Preflight a bounded classic ZIP directory before allocating ZipInfo objects."""

    try:
        stream.seek(0, os.SEEK_END)
        archive_bytes = stream.tell()
        if archive_bytes < DOCX_CLASSIC_EOCD_BYTES:
            return False
        scan_bytes = min(
            archive_bytes,
            DOCX_CLASSIC_EOCD_BYTES + DOCX_MAX_COMMENT_BYTES,
        )
        stream.seek(-scan_bytes, os.SEEK_END)
        tail = stream.read(scan_bytes)
        eocd_in_tail = tail.rfind(b"PK\x05\x06")
        if eocd_in_tail < 0 or len(tail) - eocd_in_tail < DOCX_CLASSIC_EOCD_BYTES:
            return False
        (
            disk_number,
            central_directory_disk,
            entries_on_disk,
            entry_count,
            central_directory_bytes,
            central_directory_offset,
            comment_bytes,
        ) = struct.unpack_from("<4H2IH", tail, eocd_in_tail + 4)
        if eocd_in_tail + DOCX_CLASSIC_EOCD_BYTES + comment_bytes != len(tail):
            return False
        eocd_offset = archive_bytes - len(tail) + eocd_in_tail
        if (
            disk_number != 0
            or central_directory_disk != 0
            or entries_on_disk != entry_count
            or entry_count in {0, 0xFFFF}
            or central_directory_bytes == 0xFFFFFFFF
            or central_directory_offset == 0xFFFFFFFF
            or entry_count > DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_MEMBERS
            or central_directory_bytes > DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_CENTRAL_DIRECTORY_BYTES
            or central_directory_bytes < entry_count * 46
            or central_directory_offset + central_directory_bytes != eocd_offset
        ):
            return False
        if eocd_offset >= 20:
            stream.seek(eocd_offset - 20)
            if stream.read(4) == b"PK\x06\x07":
                return False
        stream.seek(central_directory_offset)
        central_directory = stream.read(central_directory_bytes)
        if len(central_directory) != central_directory_bytes:
            return False
        central_directory_cursor = 0
        actual_entry_count = 0
        while central_directory_cursor < central_directory_bytes:
            if central_directory_bytes - central_directory_cursor < 46:
                return False
            (
                signature,
                _version_made_by,
                _version_needed,
                _flags,
                _compression,
                _modified_time,
                _modified_date,
                _crc,
                _compressed_size,
                _uncompressed_size,
                filename_bytes,
                extra_bytes,
                entry_comment_bytes,
                _disk_start,
                _internal_attributes,
                _external_attributes,
                _local_header_offset,
            ) = struct.unpack_from(
                "<4s6H3I5H2I",
                central_directory,
                central_directory_cursor,
            )
            if signature != b"PK\x01\x02":
                return False
            actual_entry_count += 1
            if actual_entry_count > DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_MEMBERS:
                return False
            central_directory_cursor += 46 + filename_bytes + extra_bytes + entry_comment_bytes
            if central_directory_cursor > central_directory_bytes:
                return False
        return (
            central_directory_cursor == central_directory_bytes
            and actual_entry_count == entry_count
        )
    except (OSError, TypeError, ValueError, struct.error):
        return False
    finally:
        try:
            stream.seek(0)
        except (OSError, ValueError):
            pass


def _document_operation_docx_stream_is_safe(stream: BinaryIO) -> bool:
    """Fully consume a bounded DOCX archive and validate every member CRC."""

    try:
        stream.seek(0)
        if not _document_operation_docx_has_safe_classic_eocd(stream):
            return False
        with ZipFile(stream, "r") as archive:
            members = archive.infolist()
            if not members or len(members) > DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_MEMBERS:
                return False
            names: set[str] = set()
            declared_total = 0
            relationship_members: list[tuple[Any, str]] = []
            required_xml_members = {
                "[Content_Types].xml": bytearray(),
                "_rels/.rels": bytearray(),
                "word/document.xml": bytearray(),
            }
            for member in members:
                name = str(member.filename or "")
                lower_name = name.casefold()
                if (
                    not _document_operation_docx_member_name_is_safe(name)
                    or member.is_dir()
                    or name in names
                    or bool(member.flag_bits & 0x1)
                    or stat.S_ISLNK(member.external_attr >> 16)
                ):
                    return False
                names.add(name)
                parts = tuple(part.casefold() for part in name.split("/"))
                if (
                    parts[-1].startswith("vba")
                    or "embeddings" in parts
                    or "activex" in parts
                ):
                    return False
                try:
                    member_size = int(member.file_size)
                except (TypeError, ValueError):
                    return False
                if member_size < 0:
                    return False
                declared_total += member_size
                if declared_total > DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_UNCOMPRESSED_BYTES:
                    return False
                if lower_name.endswith(".rels"):
                    relationship_members.append((member, lower_name))
            if not {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}.issubset(names):
                return False

            consumed_total = 0
            for member in members:
                member_name = str(member.filename)
                relationship_bytes = bytearray() if member_name.casefold().endswith(".rels") else None
                required_xml_bytes = required_xml_members.get(member_name)
                consumed_member = 0
                with archive.open(member, "r") as member_stream:
                    while True:
                        chunk = member_stream.read(CHUNK_BYTES)
                        if not chunk:
                            break
                        consumed_member += len(chunk)
                        consumed_total += len(chunk)
                        if (
                            consumed_member > int(member.file_size)
                            or consumed_total > DOCUMENT_OPERATION_ASSET_EXPORT_DOCX_MAX_UNCOMPRESSED_BYTES
                        ):
                            return False
                        if relationship_bytes is not None:
                            relationship_bytes.extend(chunk)
                        if required_xml_bytes is not None:
                            required_xml_bytes.extend(chunk)
                # Exhausting the ZipExtFile before close makes ``zipfile``
                # verify the member CRC; never treat central-directory claims
                # alone as a valid OOXML payload.
                if consumed_member != int(member.file_size):
                    return False
                if relationship_bytes is not None and not _document_operation_docx_relationships_are_safe(bytes(relationship_bytes)):
                    return False
            if not _document_operation_docx_content_types_are_valid(
                bytes(required_xml_members["[Content_Types].xml"]),
            ):
                return False
            if not _document_operation_docx_package_relationships_are_valid(
                bytes(required_xml_members["_rels/.rels"]),
            ):
                return False
            if not _document_operation_docx_required_xml_is_valid(
                bytes(required_xml_members["word/document.xml"]),
                expected_tag="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document",
            ):
                return False
            return consumed_total == declared_total
    except (BadZipFile, NotImplementedError, OSError, RuntimeError, ValueError):
        return False
    finally:
        try:
            stream.seek(0)
        except (OSError, ValueError):
            pass


def _verify_document_operation_asset_export_destination_docx(
    path: Path,
    *,
    expected_bytes: int,
    expected_digest: str,
) -> bool:
    """Validate an OOXML output and rehash its exact pinned descriptor."""

    stream = _open_verified_private_file(
        path,
        expected_bytes=expected_bytes,
        expected_digest=expected_digest,
    )
    if stream is None:
        return False
    try:
        if not _document_operation_docx_stream_is_safe(stream):
            return False
        return _verify_pinned_private_file(
            stream,
            expected_bytes=expected_bytes,
            expected_digest=expected_digest,
        )
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _verify_document_operation_asset_export_destination_text(
    path: Path,
    *,
    expected_bytes: int,
    expected_digest: str,
) -> bool:
    """Validate bounded strict UTF-8 text and rehash its pinned descriptor."""

    if expected_bytes < 1 or expected_bytes > DOCUMENT_OPERATION_ASSET_EXPORT_TEXT_MAX_BYTES:
        return False
    stream = _open_verified_private_file(
        path,
        expected_bytes=expected_bytes,
        expected_digest=expected_digest,
    )
    if stream is None:
        return False
    try:
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        has_non_whitespace = False
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            text = decoder.decode(chunk, final=False)
            if "\x00" in text:
                return False
            has_non_whitespace = has_non_whitespace or bool(text.strip())
        tail = decoder.decode(b"", final=True)
        if "\x00" in tail:
            return False
        has_non_whitespace = has_non_whitespace or bool(tail.strip())
        if not has_non_whitespace:
            return False
        return _verify_pinned_private_file(
            stream,
            expected_bytes=expected_bytes,
            expected_digest=expected_digest,
        )
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _verify_document_operation_asset_export_destination(
    path: Path,
    *,
    extension: str,
    expected_bytes: int,
    expected_digest: str,
) -> bool:
    """Dispatch only the server-selected output validator for this export."""

    if extension == ".pdf":
        return _verify_document_operation_asset_export_destination_pdf(
            path,
            expected_bytes=expected_bytes,
            expected_digest=expected_digest,
        )
    if extension == ".docx":
        return _verify_document_operation_asset_export_destination_docx(
            path,
            expected_bytes=expected_bytes,
            expected_digest=expected_digest,
        )
    if extension == ".txt":
        return _verify_document_operation_asset_export_destination_text(
            path,
            expected_bytes=expected_bytes,
            expected_digest=expected_digest,
        )
    return False


def _pdf_has_terminal_eof(stream: BinaryIO, *, expected_bytes: int) -> bool:
    """Require the final PDF EOF marker to have only PDF whitespace after it."""

    try:
        if expected_bytes < len(b"%%EOF"):
            return False
        stream.seek(0, os.SEEK_END)
        if stream.tell() != expected_bytes:
            return False
        scan_bytes = min(expected_bytes, PDF_EOF_SCAN_BYTES)
        stream.seek(-scan_bytes, os.SEEK_END)
        tail = stream.read(scan_bytes)
        marker = tail.rfind(b"%%EOF")
        return marker >= 0 and not tail[marker + len(b"%%EOF"):].strip(PDF_TRAILING_WHITESPACE)
    except (OSError, ValueError):
        return False


def _document_operation_output_filename_has_provenance(
    *,
    kind: str,
    original_filename: object,
    selected_start_page: object,
    selected_end_page: object,
    source_page_count: object,
    output_page_count: object,
) -> bool:
    """Match only filenames emitted by the real completion writer for ``kind``."""

    if not isinstance(original_filename, str):
        return False
    if kind != "pdf_split":
        return original_filename == DOCUMENT_OPERATION_ASSET_EXPORT_OUTPUT_FILENAMES.get(kind)
    page_values = (
        selected_start_page,
        selected_end_page,
        source_page_count,
        output_page_count,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) for value in page_values):
        return False
    start_page, end_page, source_pages, output_pages = page_values
    return (
        1 <= start_page <= end_page <= source_pages
        and output_pages == end_page - start_page + 1
        and original_filename == f"toan-aas-pdf-pages-{start_page}-{end_page}.pdf"
    )


def finalize_document_operation_asset_export(
    *,
    lease: DocumentOperationAssetExportLease,
    source: DocumentOperationAssetExportSource,
    request_id: str,
) -> DocumentOperationAssetExportFinalization:
    """Finalize one current fenced Document Operation output privately.

    The output contract comes only from the local server-owned kind map.  The
    caller's descriptor supplies a pre-opened source stream, never a path,
    URL, browser bytes, or output metadata that can widen that contract.
    """

    final_path: Path | None = None
    staging: Path | None = None
    owns_final_path = False
    completed = False
    try:
        _require_document_operation_asset_export_enabled()
        try:
            expected_bytes = _document_operation_export_expected_bytes(lease.reserved_bytes)
            source_digest = _export_request_fingerprint(source.sha256)
            lease_fingerprint = _export_request_fingerprint(lease.request_fingerprint)
        except HTTPException as exc:
            raise RuntimeError("Nguồn Document Operation không khớp export lease") from exc
        expected_spec = (
            DOCUMENT_OPERATION_ASSET_EXPORT_SPECS.get(source.kind)
            if isinstance(source.kind, str)
            else None
        )
        if expected_spec is None:
            raise RuntimeError("Loại Document Operation không có export Asset Vault hợp lệ")
        expected_extension, expected_content_type, expected_filename = expected_spec
        if (
            source.account_id != lease.account_id
            or source.operation_id != lease.operation_id
            or source.extension != expected_extension
            or source.content_type != expected_content_type
            or source.original_filename != expected_filename
            or isinstance(source.byte_size, bool)
            or not isinstance(source.byte_size, int)
            or source.byte_size != expected_bytes
            or source.byte_size > _maximum_bytes()
            or not hmac.compare_digest(source_digest, lease_fingerprint)
        ):
            raise RuntimeError("Nguồn Document Operation không khớp export lease")
        try:
            original_filename, extension = _safe_filename(expected_filename)
        except HTTPException as exc:
            raise RuntimeError("Tên tệp Document Operation không hợp lệ") from exc
        if original_filename != expected_filename or extension != expected_extension:
            raise RuntimeError("Tên tệp Document Operation không khớp nguồn máy chủ")

        root = asset_vault_directory()
        staging = _staging_path(root)
        copied_bytes, copied_digest = _copy_document_operation_asset_export_source(source, staging)
        final_path = _storage_path(root, lease.pending_storage_key)
        _private_asset_vault_child_directory(root, "objects")
        _promote_image_operation_export_staging(staging, final_path)
        staging = None
        owns_final_path = True
        if not _verify_document_operation_asset_export_destination(
            final_path,
            extension=expected_extension,
            expected_bytes=copied_bytes,
            expected_digest=copied_digest,
        ):
            raise RuntimeError(
                f"{expected_extension.removeprefix('.').upper()} đã sao chép không vượt qua kiểm tra Asset Vault"
            )

        asset_id = str(uuid.uuid4())
        resolved_project_id: str | None = None
        with transaction() as conn:
            # ``transaction`` has acquired SQLite's write lock before yielding
            # here.  Sample one time for both quota reservations and the
            # expiry fence so a lease cannot expire while waiting for that
            # lock and still be finalized against an older timestamp.
            now = utc_now()
            fence_now = datetime.fromisoformat(now)
            if fence_now.tzinfo is None:
                raise RuntimeError("Thời điểm export lease không hợp lệ")
            operation = conn.execute(
                """SELECT state, kind, sha256, byte_size, project_id, content_type,
                          storage_key, original_filename, selected_start_page,
                          selected_end_page, source_page_count, output_page_count
                   FROM web_document_operations WHERE id=? AND account_id=?""",
                (lease.operation_id, lease.account_id),
            ).fetchone()
            operation_project_id = str(operation[4]) if operation and operation[4] else None
            operation_kind = str(operation[1] or "") if operation else ""
            current_spec = DOCUMENT_OPERATION_ASSET_EXPORT_SPECS.get(operation_kind)
            if (
                not operation
                or str(operation[0] or "") != "completed"
                or operation_kind != source.kind
                or current_spec != expected_spec
                or not hmac.compare_digest(str(operation[2] or ""), source_digest)
                or int(operation[3] or 0) != copied_bytes
                or source.project_id != operation_project_id
                or str(operation[5] or "") != expected_content_type
                or re.fullmatch(
                    rf"outputs/[0-9a-f]{{32}}{re.escape(expected_extension)}",
                    str(operation[6] or ""),
                ) is None
                or not _document_operation_output_filename_has_provenance(
                    kind=operation_kind,
                    original_filename=operation[7],
                    selected_start_page=operation[8],
                    selected_end_page=operation[9],
                    source_page_count=operation[10],
                    output_page_count=operation[11],
                )
            ):
                raise RuntimeError("Nguồn Document Operation không còn khớp export lease")
            if operation_project_id:
                project = conn.execute(
                    "SELECT id FROM web_projects WHERE id=? AND account_id=? AND state='active'",
                    (operation_project_id, lease.account_id),
                ).fetchone()
                if project:
                    resolved_project_id = str(project[0])
            # The current lease remains part of pending capacity until the
            # fenced relation update clears it later in this same transaction.
            if not _quota_available(
                conn,
                lease.account_id,
                0,
                reference_now=fence_now,
            ):
                raise HTTPException(status_code=413, detail="Asset Vault đã đạt quota của Web account")
            conn.execute(
                """INSERT INTO web_asset_files
                   (id, account_id, project_id, display_name, original_filename, extension, content_type,
                    byte_size, sha256, storage_key, state, created_at, updated_at, archived_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, NULL)""",
                (
                    asset_id,
                    lease.account_id,
                    resolved_project_id,
                    f"Bản sao {original_filename}",
                    original_filename,
                    expected_extension,
                    expected_content_type,
                    copied_bytes,
                    copied_digest,
                    lease.pending_storage_key,
                    now,
                    now,
                ),
            )
            updated = conn.execute(
                """UPDATE web_document_operation_asset_exports
                   SET asset_id=?, state='completed', lease_token=NULL, lease_expires_at=NULL,
                       reserved_bytes=0, pending_storage_key=NULL, completed_at=?, updated_at=?
                   WHERE operation_id=? AND account_id=? AND state='copying'
                     AND request_fingerprint=? AND lease_generation=? AND lease_token=?
                     AND lease_expires_at=? AND lease_expires_at > ? AND reserved_bytes=?
                     AND pending_storage_key=? AND asset_id IS NULL""",
                (
                    asset_id,
                    now,
                    now,
                    lease.operation_id,
                    lease.account_id,
                    lease_fingerprint,
                    lease.generation,
                    lease.token,
                    lease.expires_at,
                    now,
                    expected_bytes,
                    lease.pending_storage_key,
                ),
            )
            if updated.rowcount != 1:
                raise RuntimeError("Document export lease không còn hiện tại khi hoàn tất Asset Vault")
            _record_audit(
                conn,
                account_id=lease.account_id,
                canonical_user_id=None,
                action="web.document_operation.export_to_asset_vault",
                request_id=str(request_id or "")[:160],
                target=asset_id,
                detail=f"kind={source.kind};bytes={copied_bytes}",
            )
        completed = True
        return DocumentOperationAssetExportFinalization(
            state="completed",
            asset={
                "id": asset_id,
                "project_id": resolved_project_id,
                "display_name": f"Bản sao {original_filename}",
                "original_filename": original_filename,
                "extension": expected_extension,
                "content_type": expected_content_type,
                "byte_size": copied_bytes,
                "state": ACTIVE_STATE,
                "created_at": now,
                "updated_at": now,
                "archived_at": None,
            },
        )
    finally:
        try:
            source.stream.close()
        except (AttributeError, OSError, ValueError):
            pass
        if staging is not None:
            _safe_unlink(staging)
        if not completed and owns_final_path:
            _safe_unlink(final_path)


def get_document_operation_asset_export_receipt(
    *,
    account_id: str,
    operation_id: str,
) -> DocumentOperationAssetExportFinalization | None:
    """Return the current relation and Asset Vault lifecycle, never a cache."""

    _require_document_operation_asset_export_enabled()
    scoped_account_id = _validate_id(account_id, label="Web account ID")
    scoped_operation_id = _document_operation_id(operation_id)
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            """SELECT export.state, export.asset_id,
                      asset.id, asset.project_id, asset.display_name, asset.original_filename,
                      asset.extension, asset.content_type, asset.byte_size, asset.state,
                      asset.created_at, asset.updated_at, asset.archived_at,
                      asset.sha256, export.request_fingerprint,
                      operation.sha256, operation.byte_size
               FROM web_document_operation_asset_exports AS export
               LEFT JOIN web_asset_files AS asset
                 ON asset.id=export.asset_id AND asset.account_id=export.account_id
               LEFT JOIN web_document_operations AS operation
                 ON operation.id=export.operation_id AND operation.account_id=export.account_id
               WHERE export.operation_id=? AND export.account_id=?""",
            (scoped_operation_id, scoped_account_id),
        ).fetchone()
    if not row:
        return None
    relation_state = str(row[0] or "")
    if relation_state != "completed":
        return DocumentOperationAssetExportFinalization(state=relation_state or "guarded", asset=None)
    with transaction() as conn:
        valid_snapshot = _completed_document_operation_asset_export_snapshot_is_valid(
            conn,
            account_id=scoped_account_id,
            operation_id=scoped_operation_id,
            asset_id=row[1],
            export_fingerprint=row[14],
        )
    if not valid_snapshot:
        return DocumentOperationAssetExportFinalization(state="guarded", asset=None)
    return DocumentOperationAssetExportFinalization(
        state="completed",
        asset=_asset_public(tuple(row[2:13])),
    )


def replay_document_operation_asset_export(
    *,
    account_id: str,
    operation_id: str,
    idempotency_key: str,
) -> DocumentOperationAssetExportFinalization | None:
    """Bind a fresh replay key to a current document-export lifecycle."""

    _require_document_operation_asset_export_enabled()
    scoped_account_id = _validate_id(account_id, label="Web account ID")
    scoped_operation_id = _document_operation_id(operation_id)
    key = _idempotency_key(idempotency_key)
    ensure_copyfast_schema()
    now = utc_now()
    with transaction() as conn:
        relation = conn.execute(
            """SELECT request_fingerprint, state, lease_expires_at, asset_id
               FROM web_document_operation_asset_exports
               WHERE operation_id=? AND account_id=?""",
            (scoped_operation_id, scoped_account_id),
        ).fetchone()
        existing_key = conn.execute(
            """SELECT operation_id FROM web_document_operation_asset_export_requests
               WHERE account_id=? AND idempotency_key=?""",
            (scoped_account_id, key),
        ).fetchone()
        if existing_key and str(existing_key[0]) != scoped_operation_id:
            raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho document export khác")
        if not relation:
            return None
        if str(relation[1] or "") == "copying" and _document_operation_export_lease_is_expired(
            str(relation[2] or "")
        ):
            return None
        if str(relation[1] or "") == "completed" and not _completed_document_operation_asset_export_snapshot_is_valid(
            conn,
            account_id=scoped_account_id,
            operation_id=scoped_operation_id,
            asset_id=relation[3],
            export_fingerprint=relation[0],
        ):
            return DocumentOperationAssetExportFinalization(state="guarded", asset=None)
        _insert_document_operation_asset_export_request_mapping(
            conn,
            account_id=scoped_account_id,
            idempotency_key=key,
            operation_id=scoped_operation_id,
            request_fingerprint=str(relation[0]),
            now=now,
        )
    return get_document_operation_asset_export_receipt(
        account_id=scoped_account_id,
        operation_id=scoped_operation_id,
    )


def _audio_operation_export_lease_from_row(row: tuple[Any, ...]) -> AudioOperationAssetExportLease:
    return AudioOperationAssetExportLease(
        account_id=str(row[1]), operation_id=str(row[0]), generation=int(row[5]),
        token=str(row[6]), expires_at=str(row[7]), reserved_bytes=int(row[8]),
        pending_storage_key=str(row[9]), request_fingerprint=str(row[4]),
    )


def _insert_audio_operation_asset_export_request_mapping(conn, *, account_id: str, idempotency_key: str, operation_id: str, request_fingerprint: str, now: str) -> None:
    row = conn.execute(
        "SELECT operation_id, request_fingerprint FROM web_audio_operation_asset_export_requests WHERE account_id=? AND idempotency_key=?",
        (account_id, idempotency_key),
    ).fetchone()
    if row:
        if str(row[0]) != operation_id or not hmac.compare_digest(str(row[1]), request_fingerprint):
            raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho audio export khác")
        return
    conn.execute(
        """INSERT INTO web_audio_operation_asset_export_requests
           (account_id, idempotency_key, operation_id, request_fingerprint, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (account_id, idempotency_key, operation_id, request_fingerprint, now, now),
    )


def _audio_operation_export_contract(target_format: object) -> tuple[str, str, str, frozenset[str]] | None:
    target = str(target_format or "").strip().lower()
    if target == "mp3":
        return (".mp3", "audio/mpeg", "mp3", frozenset({"mp3"}))
    if target == "m4a":
        return (".m4a", "audio/mp4", "aac", frozenset({"mov", "mp4", "m4a"}))
    return None


def _audio_operation_export_format_name_matches(value: object, accepted: frozenset[str]) -> bool:
    names = {item.strip().lower() for item in str(value or "").split(",") if item.strip()}
    return bool(names & accepted)


def _audio_operation_export_profile_is_canonical(kind: object, normalization_profile: object) -> bool:
    return (
        (kind == "audio_normalize" and normalization_profile == "speech_safe_v1")
        or (kind == "audio_convert" and normalization_profile is None)
    )


def _audio_operation_asset_export_not_ready() -> HTTPException:
    detail = "Audio Operation chưa sẵn sàng để lưu"
    error = HTTPException(status_code=409, detail=detail)
    error.args = (detail,)
    return error


def _audio_operation_export_source_provenance_mismatch(
    source: AudioOperationAssetExportSource, *, operation_kind: object, operation_project_id: object
) -> str | None:
    if source.kind != operation_kind:
        return "kind"
    if source.project_id != operation_project_id:
        return "project"
    return None


def _audio_operation_export_magic_matches(target: str, prefix: bytes) -> bool:
    if target == "mp3":
        return prefix.startswith(b"ID3") or (len(prefix) >= 2 and prefix[0] == 0xFF and (prefix[1] & 0xE0) == 0xE0)
    return len(prefix) >= 12 and prefix[4:8] == b"ftyp"


def _copy_audio_operation_asset_export_source(source: AudioOperationAssetExportSource, destination: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    copied = 0
    try:
        source.stream.seek(0)
        with destination.open("xb") as staged:
            while True:
                chunk = source.stream.read(CHUNK_BYTES)
                if not chunk:
                    break
                copied += len(chunk)
                if copied > source.byte_size or copied > _maximum_bytes():
                    raise RuntimeError("Audio Operation vượt giới hạn Asset Vault")
                digest.update(chunk)
                staged.write(chunk)
            staged.flush()
            os.fsync(staged.fileno())
    except Exception:
        _safe_unlink(destination)
        raise
    if copied != source.byte_size or not hmac.compare_digest(digest.hexdigest(), source.sha256):
        _safe_unlink(destination)
        raise RuntimeError("Audio Operation không còn integrity")
    return copied, digest.hexdigest()


def _verify_audio_operation_asset_export_destination(path: Path, *, target_format: str, expected_bytes: int, expected_digest: str) -> bool:
    stream = _open_verified_private_file(path, expected_bytes=expected_bytes, expected_digest=expected_digest)
    if stream is None:
        return False
    try:
        prefix = stream.read(32)
        return _audio_operation_export_magic_matches(target_format, prefix) and _verify_pinned_private_file(
            stream, expected_bytes=expected_bytes, expected_digest=expected_digest
        )
    except OSError:
        return False
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _completed_audio_operation_asset_export_snapshot_is_valid(conn, *, account_id: str, operation_id: str, asset_id: object, export_fingerprint: object) -> bool:
    row = conn.execute(
        """SELECT operation.state, operation.kind, operation.target_format, operation.sha256, operation.byte_size,
                  operation.content_type, operation.storage_key, operation.original_filename,
                  asset.extension, asset.content_type, asset.original_filename, asset.storage_key,
                  asset.byte_size, asset.sha256, asset.state, operation.normalization_profile
           FROM web_audio_asset_operations AS operation
           JOIN web_asset_files AS asset ON asset.id=? AND asset.account_id=operation.account_id
           WHERE operation.id=? AND operation.account_id=?""",
        (asset_id, operation_id, account_id),
    ).fetchone()
    if (
        not row
        or str(row[0]) != "completed"
        or str(row[1]) not in {"audio_convert", "audio_normalize"}
        or not _audio_operation_export_profile_is_canonical(row[1], row[15])
    ):
        return False
    spec = _audio_operation_export_contract(row[2])
    if spec is None:
        return False
    extension, content_type, _codec, _names = spec
    values = tuple(str(value or "").strip().lower() for value in (export_fingerprint, row[3], row[13]))
    if not all(re.fullmatch(r"[0-9a-f]{64}", value) for value in values):
        return False
    try:
        operation_bytes, asset_bytes = int(row[4]), int(row[12])
    except (TypeError, ValueError):
        return False
    return (
        operation_bytes > 0 and operation_bytes == asset_bytes
        and str(row[5] or "") == content_type
        and re.fullmatch(rf"outputs/[0-9a-f]{{32}}{re.escape(extension)}", str(row[6] or "")) is not None
        and str(row[7] or "") == f"toan-aas-audio{extension}"
        and str(row[8] or "") == extension and str(row[9] or "") == content_type
        and str(row[10] or "") == f"toan-aas-audio{extension}"
        and STORAGE_KEY_PATTERN.fullmatch(str(row[11] or "")) is not None
        and str(row[14] or "") == ACTIVE_STATE
        and all(hmac.compare_digest(values[0], value) for value in values[1:])
    )


def reserve_audio_operation_asset_export(
    *,
    account_id: str,
    operation_id: str,
    idempotency_key: str,
    request_fingerprint: str | None = None,
    expected_bytes: int | None = None,
) -> AudioOperationAssetExportReservation:
    """Reserve one fenced copy from DB-bound output metadata before file I/O.

    Route callers deliberately omit the optional descriptor values: the only
    safe reservation inputs are then derived from the completed operation row
    within this transaction.  Existing internal integrity tests may still
    supply both values to prove that a source descriptor matches the row.
    """
    _require_audio_operation_asset_export_enabled()
    scoped_account_id = _validate_id(account_id, label="Web account ID")
    scoped_operation_id = _audio_operation_id(operation_id)
    key = _idempotency_key(idempotency_key)
    ensure_copyfast_schema()
    now = utc_now()
    reclaimed_pending_storage_key: str | None = None
    with transaction() as conn:
        operation = conn.execute(
            "SELECT state, kind, sha256, byte_size, target_format, content_type, storage_key, original_filename, normalization_profile FROM web_audio_asset_operations WHERE id=? AND account_id=?",
            (scoped_operation_id, scoped_account_id),
        ).fetchone()
        spec = _audio_operation_export_contract(operation[4] if operation else None)
        if not operation:
            raise HTTPException(status_code=404, detail="Không tìm thấy thao tác audio thuộc Web account hiện tại")
        if (
            str(operation[0]) != "completed"
            or str(operation[1]) not in {"audio_convert", "audio_normalize"}
            or not _audio_operation_export_profile_is_canonical(operation[1], operation[8])
            or spec is None
        ):
            raise _audio_operation_asset_export_not_ready()
        extension, content_type, _codec, _names = spec
        try:
            stored_fingerprint = _export_request_fingerprint(str(operation[2] or ""))
            stored_bytes = _audio_operation_export_expected_bytes(operation[3])
        except HTTPException as exc:
            raise HTTPException(status_code=409, detail="Audio export này không còn khớp output đã xác minh") from exc
        fingerprint = (
            stored_fingerprint
            if request_fingerprint is None
            else _export_request_fingerprint(request_fingerprint)
        )
        byte_size = (
            stored_bytes
            if expected_bytes is None
            else _audio_operation_export_expected_bytes(expected_bytes)
        )
        if (not hmac.compare_digest(stored_fingerprint, fingerprint) or stored_bytes != byte_size
                or str(operation[5] or "") != content_type
                or re.fullmatch(rf"outputs/[0-9a-f]{{32}}{re.escape(extension)}", str(operation[6] or "")) is None
                or str(operation[7] or "") != f"toan-aas-audio{extension}"):
            raise HTTPException(status_code=409, detail="Audio export này không còn khớp output đã xác minh")
        relation = conn.execute(
            """SELECT operation_id, account_id, asset_id, state, request_fingerprint, lease_generation,
                      lease_token, lease_expires_at, reserved_bytes, pending_storage_key
               FROM web_audio_operation_asset_exports WHERE operation_id=? AND account_id=?""",
            (scoped_operation_id, scoped_account_id),
        ).fetchone()
        if relation:
            if not hmac.compare_digest(str(relation[4]), fingerprint):
                raise HTTPException(status_code=409, detail="Audio export này không còn khớp output đã xác minh")
            if str(relation[3]) == "completed":
                if not _completed_audio_operation_asset_export_snapshot_is_valid(conn, account_id=scoped_account_id, operation_id=scoped_operation_id, asset_id=relation[2], export_fingerprint=relation[4]):
                    return AudioOperationAssetExportReservation(state="guarded")
                _insert_audio_operation_asset_export_request_mapping(conn, account_id=scoped_account_id, idempotency_key=key, operation_id=scoped_operation_id, request_fingerprint=fingerprint, now=now)
                return AudioOperationAssetExportReservation(state="completed")
            if int(relation[8]) != byte_size:
                raise HTTPException(status_code=409, detail="Audio export này không còn khớp kích thước đã xác minh")
            _insert_audio_operation_asset_export_request_mapping(conn, account_id=scoped_account_id, idempotency_key=key, operation_id=scoped_operation_id, request_fingerprint=fingerprint, now=now)
            if str(relation[3]) != "copying" or not _audio_operation_export_lease_is_expired(str(relation[7] or "")):
                return AudioOperationAssetExportReservation(state="pending")
            if not _quota_available(conn, scoped_account_id, byte_size):
                raise HTTPException(status_code=413, detail="Asset Vault đã đạt quota của Web account")
            generation, token, expires_at, pending_key = int(relation[5]) + 1, uuid.uuid4().hex, _audio_operation_export_lease_expiry(), _audio_operation_export_pending_storage_key()
            updated = conn.execute(
                """UPDATE web_audio_operation_asset_exports SET lease_generation=?, lease_token=?, lease_expires_at=?, pending_storage_key=?, updated_at=?
                   WHERE operation_id=? AND account_id=? AND state='copying' AND lease_generation=? AND lease_token=? AND lease_expires_at=?""",
                (generation, token, expires_at, pending_key, now, scoped_operation_id, scoped_account_id, relation[5], relation[6], relation[7]),
            )
            if updated.rowcount != 1:
                return AudioOperationAssetExportReservation(state="pending")
            old_pending_key = str(relation[9] or "")
            if old_pending_key and old_pending_key != pending_key:
                reclaimed_pending_storage_key = old_pending_key
        else:
            if not _quota_available(conn, scoped_account_id, byte_size):
                raise HTTPException(status_code=413, detail="Asset Vault đã đạt quota của Web account")
            generation, token, expires_at, pending_key = 1, uuid.uuid4().hex, _audio_operation_export_lease_expiry(), _audio_operation_export_pending_storage_key()
            conn.execute(
                """INSERT INTO web_audio_operation_asset_exports (operation_id, account_id, asset_id, state, request_fingerprint, lease_generation, lease_token, lease_expires_at, reserved_bytes, pending_storage_key, created_at, updated_at, completed_at)
                   VALUES (?, ?, NULL, 'copying', ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
                (scoped_operation_id, scoped_account_id, fingerprint, generation, token, expires_at, byte_size, pending_key, now, now),
            )
            _insert_audio_operation_asset_export_request_mapping(conn, account_id=scoped_account_id, idempotency_key=key, operation_id=scoped_operation_id, request_fingerprint=fingerprint, now=now)
    if reclaimed_pending_storage_key is not None:
        _cleanup_reclaimed_audio_operation_export_blob(reclaimed_pending_storage_key)
    return AudioOperationAssetExportReservation(state="leased", lease=AudioOperationAssetExportLease(scoped_account_id, scoped_operation_id, generation, token, expires_at, pending_key, byte_size, fingerprint))


def release_audio_operation_asset_export_lease(lease: AudioOperationAssetExportLease) -> bool:
    ensure_copyfast_schema()
    now = utc_now()
    with transaction() as conn:
        updated = conn.execute(
            """UPDATE web_audio_operation_asset_exports SET lease_expires_at=?, updated_at=?
               WHERE operation_id=? AND account_id=? AND state='copying' AND lease_generation=? AND lease_token=? AND lease_expires_at=? AND lease_expires_at > ?""",
            (now, now, lease.operation_id, lease.account_id, lease.generation, lease.token, lease.expires_at, now),
        )
    return updated.rowcount == 1


def finalize_audio_operation_asset_export(*, lease: AudioOperationAssetExportLease, source: AudioOperationAssetExportSource, request_id: str) -> AudioOperationAssetExportFinalization:
    """Copy only a current server-derived MP3/M4A output into Asset Vault."""
    final_path: Path | None = None
    staging: Path | None = None
    owns_final_path = False
    completed = False
    try:
        _require_audio_operation_asset_export_enabled()
        try:
            expected_bytes = _audio_operation_export_expected_bytes(lease.reserved_bytes)
            digest = _export_request_fingerprint(source.sha256)
            fingerprint = _export_request_fingerprint(lease.request_fingerprint)
        except HTTPException as exc:
            raise RuntimeError("Nguồn Audio Operation không khớp export lease") from exc
        spec = _audio_operation_export_contract(source.target_format)
        if spec is None:
            raise RuntimeError("Định dạng Audio Operation không có export Asset Vault hợp lệ")
        extension, content_type, codec, format_names = spec
        if (
            source.account_id != lease.account_id or source.operation_id != lease.operation_id
            or source.kind not in {"audio_convert", "audio_normalize"}
            or source.extension != extension or source.content_type != content_type
            or source.original_filename != f"toan-aas-audio{extension}"
            or isinstance(source.byte_size, bool) or not isinstance(source.byte_size, int)
            or source.byte_size != expected_bytes or source.byte_size > _maximum_bytes()
            or not hmac.compare_digest(digest, fingerprint)
            or source.codec != codec or source.sample_rate != 48000 or source.channels not in {1, 2}
            or not isinstance(source.duration_ms, int) or source.duration_ms < 1
            or not isinstance(source.duration_seconds, (int, float)) or isinstance(source.duration_seconds, bool)
            or not math.isfinite(float(source.duration_seconds)) or source.duration_seconds <= 0
            or abs(float(source.duration_seconds) * 1000 - source.duration_ms) > 1.0
            or not _audio_operation_export_format_name_matches(source.format_name, format_names)
        ):
            raise RuntimeError("Nguồn Audio Operation không khớp export lease")
        with transaction() as conn:
            operation = conn.execute(
                "SELECT kind, project_id, normalization_profile FROM web_audio_asset_operations WHERE id=? AND account_id=?",
                (lease.operation_id, lease.account_id),
            ).fetchone()
            if not operation or not _audio_operation_export_profile_is_canonical(operation[0], operation[2]):
                raise RuntimeError("Nguồn Audio Operation không còn khớp export lease")
            mismatch = _audio_operation_export_source_provenance_mismatch(
                source, operation_kind=operation[0], operation_project_id=operation[1]
            )
            if mismatch:
                raise RuntimeError(f"Nguồn Audio Operation {mismatch} không khớp export lease")
        root = asset_vault_directory()
        staging = _staging_path(root)
        copied_bytes, copied_digest = _copy_audio_operation_asset_export_source(source, staging)
        final_path = _storage_path(root, lease.pending_storage_key)
        _private_asset_vault_child_directory(root, "objects")
        _promote_image_operation_export_staging(staging, final_path)
        staging = None
        owns_final_path = True
        if not _verify_audio_operation_asset_export_destination(final_path, target_format=str(source.target_format), expected_bytes=copied_bytes, expected_digest=copied_digest):
            raise RuntimeError("Audio đã sao chép không vượt qua kiểm tra Asset Vault")

        asset_id = str(uuid.uuid4())
        resolved_project_id: str | None = None
        with transaction() as conn:
            now = utc_now()
            operation = conn.execute(
                """SELECT state, kind, target_format, sha256, byte_size, project_id, content_type, storage_key,
                          original_filename, output_duration_ms, output_channels, output_sample_rate, output_codec,
                          normalization_profile
                   FROM web_audio_asset_operations WHERE id=? AND account_id=?""",
                (lease.operation_id, lease.account_id),
            ).fetchone()
            if not operation:
                raise RuntimeError("Nguồn Audio Operation không còn khớp export lease")
            operation_spec = _audio_operation_export_contract(operation[2])
            if (
                str(operation[0]) != "completed" or str(operation[1]) not in {"audio_convert", "audio_normalize"}
                or not _audio_operation_export_profile_is_canonical(operation[1], operation[13])
                or _audio_operation_export_source_provenance_mismatch(
                    source, operation_kind=operation[1], operation_project_id=operation[5]
                ) is not None
                or operation_spec != spec or not hmac.compare_digest(str(operation[3] or ""), digest)
                or int(operation[4] or 0) != copied_bytes or str(operation[6] or "") != content_type
                or re.fullmatch(rf"outputs/[0-9a-f]{{32}}{re.escape(extension)}", str(operation[7] or "")) is None
                or str(operation[8] or "") != f"toan-aas-audio{extension}"
                or int(operation[9] or 0) != source.duration_ms or int(operation[10] or 0) != source.channels
                or int(operation[11] or 0) != source.sample_rate or str(operation[12] or "") != codec
            ):
                raise RuntimeError("Nguồn Audio Operation không còn khớp export lease")
            operation_project_id = str(operation[5]) if operation[5] else None
            if operation_project_id:
                project = conn.execute("SELECT id FROM web_projects WHERE id=? AND account_id=? AND state='active'", (operation_project_id, lease.account_id)).fetchone()
                if project:
                    resolved_project_id = str(project[0])
            fence_now = datetime.fromisoformat(now)
            if fence_now.tzinfo is None or not _quota_available(conn, lease.account_id, 0, reference_now=fence_now):
                raise HTTPException(status_code=413, detail="Asset Vault đã đạt quota của Web account")
            conn.execute(
                """INSERT INTO web_asset_files (id, account_id, project_id, display_name, original_filename, extension, content_type, byte_size, sha256, storage_key, state, created_at, updated_at, archived_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, NULL)""",
                (asset_id, lease.account_id, resolved_project_id, f"Bản sao toan-aas-audio{extension}", f"toan-aas-audio{extension}", extension, content_type, copied_bytes, copied_digest, lease.pending_storage_key, now, now),
            )
            updated = conn.execute(
                """UPDATE web_audio_operation_asset_exports SET asset_id=?, state='completed', lease_token=NULL, lease_expires_at=NULL, reserved_bytes=0, pending_storage_key=NULL, completed_at=?, updated_at=?
                   WHERE operation_id=? AND account_id=? AND state='copying' AND request_fingerprint=?
                     AND lease_generation=? AND lease_token=? AND lease_expires_at=? AND lease_expires_at > ?
                     AND reserved_bytes=? AND pending_storage_key=? AND asset_id IS NULL""",
                (asset_id, now, now, lease.operation_id, lease.account_id, fingerprint, lease.generation, lease.token, lease.expires_at, now, expected_bytes, lease.pending_storage_key),
            )
            if updated.rowcount != 1:
                raise RuntimeError("Audio export lease không còn hiện tại khi hoàn tất Asset Vault")
            _record_audit(conn, account_id=lease.account_id, canonical_user_id=None, action="web.audio_operation.export_to_asset_vault", request_id=str(request_id or "")[:160], target=asset_id, detail=f"kind={source.kind};format={source.target_format};bytes={copied_bytes}")
        completed = True
        return AudioOperationAssetExportFinalization(state="completed", asset={
            "id": asset_id, "project_id": resolved_project_id, "display_name": f"Bản sao toan-aas-audio{extension}",
            "original_filename": f"toan-aas-audio{extension}", "extension": extension, "content_type": content_type,
            "byte_size": copied_bytes, "state": ACTIVE_STATE, "created_at": now, "updated_at": now, "archived_at": None,
        })
    finally:
        try:
            source.stream.close()
        except (AttributeError, OSError, ValueError):
            pass
        if staging is not None:
            _safe_unlink(staging)
        if not completed and owns_final_path:
            _safe_unlink(final_path)


def get_audio_operation_asset_export_receipt(*, account_id: str, operation_id: str) -> AudioOperationAssetExportFinalization | None:
    _require_audio_operation_asset_export_enabled()
    scoped_account_id = _validate_id(account_id, label="Web account ID")
    scoped_operation_id = _audio_operation_id(operation_id)
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            """SELECT export.state, export.asset_id, asset.id, asset.project_id, asset.display_name, asset.original_filename,
                      asset.extension, asset.content_type, asset.byte_size, asset.state, asset.created_at, asset.updated_at, asset.archived_at,
                      export.request_fingerprint
               FROM web_audio_operation_asset_exports AS export
               LEFT JOIN web_asset_files AS asset ON asset.id=export.asset_id AND asset.account_id=export.account_id
               WHERE export.operation_id=? AND export.account_id=?""",
            (scoped_operation_id, scoped_account_id),
        ).fetchone()
        if not row:
            return None
        if str(row[0] or "") != "completed":
            return AudioOperationAssetExportFinalization(state=str(row[0] or "guarded"), asset=None)
        if not _completed_audio_operation_asset_export_snapshot_is_valid(conn, account_id=scoped_account_id, operation_id=scoped_operation_id, asset_id=row[1], export_fingerprint=row[13]):
            return AudioOperationAssetExportFinalization(state="guarded", asset=None)
    return AudioOperationAssetExportFinalization(state="completed", asset=_asset_public(tuple(row[2:13])))


def replay_audio_operation_asset_export(*, account_id: str, operation_id: str, idempotency_key: str) -> AudioOperationAssetExportFinalization | None:
    _require_audio_operation_asset_export_enabled()
    scoped_account_id = _validate_id(account_id, label="Web account ID")
    scoped_operation_id = _audio_operation_id(operation_id)
    key = _idempotency_key(idempotency_key)
    ensure_copyfast_schema()
    now = utc_now()
    with transaction() as conn:
        relation = conn.execute("SELECT request_fingerprint, state, lease_expires_at, asset_id FROM web_audio_operation_asset_exports WHERE operation_id=? AND account_id=?", (scoped_operation_id, scoped_account_id)).fetchone()
        existing = conn.execute("SELECT operation_id FROM web_audio_operation_asset_export_requests WHERE account_id=? AND idempotency_key=?", (scoped_account_id, key)).fetchone()
        if existing and str(existing[0]) != scoped_operation_id:
            raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho audio export khác")
        if not relation or (str(relation[1] or "") == "copying" and _audio_operation_export_lease_is_expired(str(relation[2] or ""))):
            return None
        if str(relation[1] or "") == "completed" and not _completed_audio_operation_asset_export_snapshot_is_valid(conn, account_id=scoped_account_id, operation_id=scoped_operation_id, asset_id=relation[3], export_fingerprint=relation[0]):
            return AudioOperationAssetExportFinalization(state="guarded", asset=None)
        _insert_audio_operation_asset_export_request_mapping(conn, account_id=scoped_account_id, idempotency_key=key, operation_id=scoped_operation_id, request_fingerprint=str(relation[0]), now=now)
    return get_audio_operation_asset_export_receipt(account_id=scoped_account_id, operation_id=scoped_operation_id)


def _ensure_project_scope(conn, *, project_id: str | None, account_id: str) -> None:
    if not project_id:
        return
    row = conn.execute(
        "SELECT id FROM web_projects WHERE id=? AND account_id=? AND state='active'",
        (project_id, account_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=422, detail="Project đính kèm không hợp lệ hoặc không còn hoạt động")


def _safe_unlink(path: Path) -> None:
    try:
        if path.is_file() and not path.is_symlink():
            path.unlink()
    except OSError:
        pass


def _same_private_file(left: os.stat_result, right: os.stat_result) -> bool:
    """Compare the identity of two file stats rather than their path text."""

    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def _private_directory_fd_supported() -> bool:
    """Whether this runtime can pin each private-storage path component."""

    supported = getattr(os, "supports_dir_fd", set())
    return bool(
        getattr(os, "O_DIRECTORY", 0)
        and getattr(os, "O_NOFOLLOW", 0)
        and os.open in supported
        and os.stat in supported
    )


def _open_private_objects_directory(path: Path) -> tuple[int, int] | None:
    """Pin the Vault root and `objects/` directory on POSIX systems.

    Opening `objects` relative to an already-open root descriptor prevents a
    sibling process from swapping that intermediate component for a symlink
    between a preliminary check and the final blob open.  The fallback is
    intentionally only for platforms without `dir_fd`; production Railway
    Linux uses this hardened branch.
    """

    if not _private_directory_fd_supported():
        return None
    root_descriptor = -1
    objects_descriptor = -1
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_BINARY", 0)
        root_descriptor = os.open(path.parent.parent, directory_flags)
        objects_descriptor = os.open("objects", directory_flags, dir_fd=root_descriptor)
        return root_descriptor, objects_descriptor
    except OSError:
        if objects_descriptor >= 0:
            os.close(objects_descriptor)
        if root_descriptor >= 0:
            os.close(root_descriptor)
        return None


def _close_private_objects_directory(descriptors: tuple[int, int] | None) -> None:
    if descriptors is None:
        return
    for descriptor in reversed(descriptors):
        try:
            os.close(descriptor)
        except OSError:
            pass


def _private_blob_stat(path: Path) -> os.stat_result | None:
    """Read final-component metadata without following an intermediate link."""

    if _private_directory_fd_supported():
        directories = _open_private_objects_directory(path)
        if directories is None:
            return None
        _root_descriptor, objects_descriptor = directories
        try:
            return os.stat(path.name, dir_fd=objects_descriptor, follow_symlinks=False)
        except OSError:
            return None
        finally:
            _close_private_objects_directory(directories)
    try:
        return os.lstat(path)
    except OSError:
        return None


def _open_verified_private_file(path: Path, *, expected_bytes: int, expected_digest: str) -> BinaryIO | None:
    """Open, hash and pin one private blob without a check/open race.

    The file descriptor, not its pathname, becomes the authority after this
    function returns.  On Linux, both the Vault root and `objects/` are pinned
    with directory descriptors and the final component is opened relative to
    that pinned directory with ``O_NOFOLLOW``.  This removes the intermediate
    directory-swap window as well as the final symlink/pathname race.
    """

    if expected_bytes <= 0 or not expected_digest:
        return None
    descriptor = -1
    stream: BinaryIO | None = None
    try:
        directories = _open_private_objects_directory(path) if _private_directory_fd_supported() else None
        if _private_directory_fd_supported() and directories is None:
            return None
        if directories is not None:
            _root_descriptor, objects_descriptor = directories
            try:
                before = os.stat(path.name, dir_fd=objects_descriptor, follow_symlinks=False)
                flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_BINARY", 0)
                descriptor = os.open(path.name, flags, dir_fd=objects_descriptor)
            finally:
                _close_private_objects_directory(directories)
        else:
            parent_stat = os.lstat(path.parent)
            before = os.lstat(path)
            if (
                stat.S_ISLNK(parent_stat.st_mode)
                or not stat.S_ISDIR(parent_stat.st_mode)
                or stat.S_ISLNK(before.st_mode)
            ):
                return None
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, flags)
        if not stat.S_ISREG(before.st_mode):
            return None
        pinned = os.fstat(descriptor)
        if (
            not stat.S_ISREG(pinned.st_mode)
            or pinned.st_size != expected_bytes
            or not _same_private_file(before, pinned)
        ):
            return None
        stream = os.fdopen(descriptor, "rb", closefd=True)
        descriptor = -1
        digest = hashlib.sha256()
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
        if not hmac.compare_digest(digest.hexdigest(), expected_digest):
            return None
        stream.seek(0)
        accepted = stream
        stream = None
        return accepted
    except (OSError, ValueError):
        return None
    finally:
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _pinned_private_file_is_current(stream: BinaryIO, path: Path) -> bool:
    """Confirm that a pinned, already-hashed descriptor still names the blob.

    This is deliberately used immediately before an archived blob transitions
    back to active.  A later download independently opens and hashes a fresh
    pinned descriptor, so a post-transition filesystem mutation also fails
    closed instead of ever being served by pathname.
    """

    try:
        current = _private_blob_stat(path)
        if current is None:
            return False
        pinned = os.fstat(stream.fileno())
        return (
            not stat.S_ISLNK(current.st_mode)
            and stat.S_ISREG(current.st_mode)
            and stat.S_ISREG(pinned.st_mode)
            and _same_private_file(current, pinned)
        )
    except (OSError, ValueError):
        return False


def _verify_pinned_private_file(stream: BinaryIO, *, expected_bytes: int, expected_digest: str) -> bool:
    """Rehash a descriptor that is already pinned to one physical blob."""

    try:
        pinned = os.fstat(stream.fileno())
        if not stat.S_ISREG(pinned.st_mode) or pinned.st_size != expected_bytes:
            return False
        stream.seek(0)
        digest = hashlib.sha256()
        read_bytes = 0
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            read_bytes += len(chunk)
            digest.update(chunk)
        stream.seek(0)
        return read_bytes == expected_bytes and hmac.compare_digest(digest.hexdigest(), expected_digest)
    except (OSError, ValueError):
        return False


def seal_verified_private_file(
    stream: BinaryIO,
    *,
    expected_bytes: int,
    expected_digest: str,
) -> BinaryIO | None:
    """Copy a verified source into an anonymous, rehashed stream for delivery.

    A pinned source descriptor prevents path swaps, but a hostile process with
    write access to the same inode could still mutate it while an HTTP response
    is streaming.  Before any private download leaves the process, copy it to
    an unnamed temporary file while hashing again.  The response then streams
    the sealed descriptor, never the mutable Vault object.
    """

    sealed: BinaryIO | None = None
    try:
        if expected_bytes <= 0 or expected_bytes > _maximum_bytes() or not expected_digest:
            return None
        sealed = tempfile.TemporaryFile(mode="w+b")
        digest = hashlib.sha256()
        read_bytes = 0
        stream.seek(0)
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            read_bytes += len(chunk)
            if read_bytes > expected_bytes:
                return None
            digest.update(chunk)
            sealed.write(chunk)
        if read_bytes != expected_bytes or not hmac.compare_digest(digest.hexdigest(), expected_digest):
            return None
        sealed.seek(0)
        accepted = sealed
        sealed = None
        return accepted
    except (OSError, ValueError):
        return None
    finally:
        try:
            stream.close()
        except OSError:
            pass
        if sealed is not None:
            try:
                sealed.close()
            except OSError:
                pass


def _verify_private_file(path: Path, *, expected_bytes: int, expected_digest: str) -> bool:
    """Compatibility predicate backed by a descriptor-pinned verification."""

    stream = _open_verified_private_file(
        path,
        expected_bytes=expected_bytes,
        expected_digest=expected_digest,
    )
    if stream is None:
        return False
    try:
        return True
    finally:
        stream.close()


def open_verified_private_asset_stream(
    *,
    storage_key: str,
    expected_bytes: int,
    expected_digest: str,
) -> BinaryIO | None:
    """Return a descriptor-pinned verified stream for a trusted Web caller.

    The caller owns and must close the returned stream.  It intentionally does
    not return a pathname: HTTP delivery must not verify one blob and later
    reopen another by path.
    """

    try:
        path = _storage_path(asset_vault_directory(), str(storage_key or ""))
    except (OSError, RuntimeError):
        return None
    return _open_verified_private_file(
        path,
        expected_bytes=expected_bytes,
        expected_digest=str(expected_digest),
    )


def _pinned_private_file_chunks(stream: BinaryIO) -> Iterator[bytes]:
    try:
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            yield chunk
    finally:
        stream.close()


def private_asset_attachment_response(
    stream: BinaryIO,
    *,
    byte_size: int,
    media_type: str,
    filename: str,
) -> StreamingResponse:
    """Serve one already-pinned private file as a never-cached attachment."""

    if byte_size <= 0:
        stream.close()
        raise ValueError("Kích thước private Asset Vault không hợp lệ")
    safe_name = str(filename or "download").replace("\r", " ").replace("\n", " ").strip() or "download"
    return StreamingResponse(
        _pinned_private_file_chunks(stream),
        media_type=media_type,
        background=BackgroundTask(stream.close),
        headers={
            "Content-Length": str(byte_size),
            "Content-Disposition": f"attachment; filename*=utf-8''{quote(safe_name)}",
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
        },
    )


def private_asset_inline_response(
    stream: BinaryIO,
    *,
    byte_size: int,
    media_type: str,
    filename: str,
) -> StreamingResponse:
    """Serve an already-pinned private media reference for same-origin preview.

    Callers must have already performed account ownership, object reference,
    media-type and integrity checks.  The response intentionally has no
    public URL, cache permission or byte-range contract; a future seek/range
    implementation requires its own storage and media-security review.
    """

    if byte_size <= 0:
        stream.close()
        raise ValueError("Kích thước private Asset Vault không hợp lệ")
    safe_name = str(filename or "preview").replace("\r", " ").replace("\n", " ").strip() or "preview"
    return StreamingResponse(
        _pinned_private_file_chunks(stream),
        media_type=media_type,
        background=BackgroundTask(stream.close),
        headers={
            "Content-Length": str(byte_size),
            "Content-Disposition": f"inline; filename*=utf-8''{quote(safe_name)}",
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
            "Cross-Origin-Resource-Policy": "same-origin",
        },
    )


def read_verified_private_asset_bytes(
    *,
    storage_key: str,
    expected_bytes: int,
    expected_digest: str,
    maximum_bytes: int,
) -> bytes | None:
    """Read a small verified private blob without creating a public handle.

    The bounded helper is used only to safety-scan a pre-existing text Asset
    Vault record before it is linked as Support Desk evidence.  It verifies
    the byte count and digest again after reading, closing the check/read
    window without retaining content in any audit/event record.
    """
    if expected_bytes <= 0 or expected_bytes > maximum_bytes:
        return None
    stream = open_verified_private_asset_stream(
        storage_key=storage_key,
        expected_bytes=expected_bytes,
        expected_digest=expected_digest,
    )
    if stream is None:
        return None
    try:
        content = stream.read(expected_bytes + 1)
    except OSError:
        return None
    finally:
        stream.close()
    if len(content) != expected_bytes:
        return None
    digest = hashlib.sha256(content).hexdigest()
    return content if hmac.compare_digest(digest, expected_digest) else None


def _mark_unavailable(asset_id: str, account_id: str) -> None:
    with transaction() as conn:
        conn.execute(
            """UPDATE web_asset_files
               SET state=?, updated_at=?, lifecycle_revision=lifecycle_revision + 1
               WHERE id=? AND account_id=? AND state IN (?, ?)""",
            (UNAVAILABLE_STATE, utc_now(), asset_id, account_id, ACTIVE_STATE, ARCHIVED_STATE),
        )


def reconcile_asset_vault_storage() -> None:
    """Bound cleanup for abandoned upload temp/final files after an interruption.

    Only files older than one hour, inside the vault's generated directories,
    and not referenced by any metadata row are removed.  The routine never
    traverses a user path or deletes a referenced private blob.
    """
    if not asset_vault_enabled():
        return
    ensure_copyfast_schema()
    root = asset_vault_directory()
    staging = _private_asset_vault_child_directory(root, ".staging")
    objects = _private_asset_vault_child_directory(root, "objects")
    with transaction() as conn:
        referenced = {
            str(row[0])
            for row in conn.execute("SELECT storage_key FROM web_asset_files").fetchall()
            if row[0]
        }
        pending_rows = conn.execute(
            """SELECT pending_storage_key, lease_expires_at
               FROM web_image_operation_asset_exports
               WHERE state='copying' AND lease_token IS NOT NULL
                 AND pending_storage_key IS NOT NULL"""
        ).fetchall()
        referenced.update(
            str(row[0])
            for row in pending_rows
            if row[0] and not _lease_is_expired(str(row[1] or ""))
        )
        pending_document_rows = conn.execute(
            """SELECT pending_storage_key, lease_expires_at
               FROM web_document_operation_asset_exports
               WHERE state='copying' AND lease_token IS NOT NULL
                 AND pending_storage_key IS NOT NULL"""
        ).fetchall()
        referenced.update(
            str(row[0])
            for row in pending_document_rows
            if row[0] and not _document_operation_export_lease_is_expired(str(row[1] or ""))
        )
        pending_audio_rows = conn.execute(
            """SELECT pending_storage_key, lease_expires_at
               FROM web_audio_operation_asset_exports
               WHERE state='copying' AND lease_token IS NOT NULL
                 AND pending_storage_key IS NOT NULL"""
        ).fetchall()
        referenced.update(
            str(row[0])
            for row in pending_audio_rows
            if row[0] and not _audio_operation_export_lease_is_expired(str(row[1] or ""))
        )
    cutoff = datetime.now(timezone.utc).timestamp() - ORPHAN_RETENTION_SECONDS
    for directory, match_key in ((staging, False), (objects, True)):
        try:
            candidates = list(directory.iterdir())
        except OSError:
            continue
        for candidate in candidates:
            try:
                if not candidate.is_file() or candidate.is_symlink() or candidate.stat().st_mtime > cutoff:
                    continue
                relative = candidate.resolve().relative_to(root.resolve()).as_posix()
            except (OSError, ValueError):
                continue
            if match_key and relative in referenced:
                continue
            _safe_unlink(candidate)


@router.get("")
async def list_assets(
    state: str = ACTIVE_STATE,
    q: str | None = None,
    project_id: str | None = None,
    reference_kind: str = "all",
    limit: int = 30,
    offset: int = 0,
    account: dict = Depends(require_account),
):
    """Return a bounded, owner-scoped Asset Vault library projection.

    The listing never contains blob paths, checksums, or a delivery URL.  It
    is deliberately page-based so an account with more than one hundred files
    does not silently lose older private records in the Web UI.
    """
    _require_enabled()
    selected_state = str(state or ACTIVE_STATE).strip().lower()
    if selected_state not in {*VISIBLE_STATES, "all"}:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái Asset Vault không hợp lệ")
    bounded_limit = max(1, min(int(limit), 100))
    bounded_offset = max(0, min(int(offset), 10_000))
    needle = _list_search(q)
    selected_reference_kind = _reference_kind(reference_kind)
    scoped_project_id = _validate_id(project_id, label="Project ID") if str(project_id or "").strip() else None
    where = ["account_id=?"]
    params: list[Any] = [str(account["id"])]
    if selected_state == "all":
        # `unavailable` is an internal integrity result.  It is never a
        # browseable library state, even when the customer asks for all files.
        where.append("state IN (?, ?)")
        params.extend([ACTIVE_STATE, ARCHIVED_STATE])
    else:
        where.append("state=?")
        params.append(selected_state)
    if scoped_project_id:
        where.append("project_id=?")
        params.append(scoped_project_id)
    if selected_reference_kind == "pdf":
        # Uploads canonicalize these two fields together.  Keep the exact
        # pair here rather than accepting a MIME prefix so a malformed row
        # cannot masquerade as a document-operation source.
        where.append("lower(extension)=? AND lower(content_type)=?")
        params.extend([".pdf", "application/pdf"])
    elif selected_reference_kind == "image":
        # Match only the raster formats native operations can decode.  Each
        # extension is paired with its canonical MIME type, avoiding a loose
        # `image/*` query that could surface unsupported or inconsistent rows.
        where.append(
            "("
            "(lower(extension)=? AND lower(content_type)=?) OR "
            "(lower(extension)=? AND lower(content_type)=?) OR "
            "(lower(extension)=? AND lower(content_type)=?) OR "
            "(lower(extension)=? AND lower(content_type)=?)"
            ")"
        )
        params.extend([
            ".jpg", "image/jpeg", ".jpeg", "image/jpeg",
            ".png", "image/png", ".webp", "image/webp",
        ])
    elif selected_reference_kind == "subtitle":
        # Subtitle asset operations accept only canonical SRT/VTT pairs.  Do
        # not treat generic text files (or an extension with a mismatched
        # MIME type) as a subtitle source merely because they are readable.
        where.append(
            "("
            "(lower(extension)=? AND lower(content_type)=?) OR "
            "(lower(extension)=? AND lower(content_type)=?)"
            ")"
        )
        params.extend([
            ".srt", "application/x-subrip",
            ".vtt", "text/vtt",
        ])
    elif selected_reference_kind == "audio":
        # Audio Asset Operations accepts only canonical Asset Vault pairs.
        # Upload normalization may accept legacy browser MIME aliases, but it
        # persists the canonical MIME above.  Pairing extension and MIME here
        # prevents a malformed row from reaching the private processor simply
        # because it happens to have an ``audio``-looking type.
        where.append(
            "("
            "(lower(extension)=? AND lower(content_type)=?) OR "
            "(lower(extension)=? AND lower(content_type)=?) OR "
            "(lower(extension)=? AND lower(content_type)=?) OR "
            "(lower(extension)=? AND lower(content_type)=?)"
            ")"
        )
        params.extend([
            ".mp3", "audio/mpeg",
            ".wav", "audio/wav",
            ".m4a", "audio/mp4",
            ".ogg", "audio/ogg",
        ])
    elif selected_reference_kind == "video_transform":
        # Video Finishing accepts only an Asset Vault MP4 with the canonical
        # MIME pair.  Do not surface MOV/WebM merely because the Vault can
        # store them: the local finisher has a deliberately narrower source
        # contract and must not ask the browser to infer codec compatibility.
        where.append("lower(extension)=? AND lower(content_type)=?")
        params.extend([".mp4", "video/mp4"])
    elif selected_reference_kind == "video_poster":
        # Video Poster has its own bounded FFmpeg contract.  It accepts the
        # three canonical Asset Vault video pairs supported by that contract;
        # never use a loose `video/*` browser filter or an all-assets list.
        where.append(
            "("
            "(lower(extension)=? AND lower(content_type)=?) OR "
            "(lower(extension)=? AND lower(content_type)=?) OR "
            "(lower(extension)=? AND lower(content_type)=?)"
            ")"
        )
        params.extend([
            ".mp4", "video/mp4",
            ".mov", "video/quicktime",
            ".webm", "video/webm",
        ])
    elif selected_reference_kind == "video_preview":
        # The browser inspector deliberately accepts only the two canonical
        # pairs with broad current browser support.  MOV stays excluded even
        # though Asset Vault can retain it, and the explicit byte ceiling
        # bounds each same-origin Blob allocation and integrity rehash.
        where.append(
            "("
            "(lower(extension)=? AND lower(content_type)=?) OR "
            "(lower(extension)=? AND lower(content_type)=?)"
            ") AND byte_size > 0 AND byte_size <= ?"
        )
        params.extend([
            ".mp4", "video/mp4",
            ".webm", "video/webm",
            VIDEO_PREVIEW_MAX_BYTES,
        ])
    if needle:
        escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("(display_name LIKE ? ESCAPE '\\' OR original_filename LIKE ? ESCAPE '\\')")
        params.extend([f"%{escaped}%", f"%{escaped}%"])
    predicate = " AND ".join(where)
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT id, project_id, display_name, original_filename, extension, content_type,
                        byte_size, state, created_at, updated_at, archived_at
                 FROM web_asset_files
                 WHERE {predicate}
                 ORDER BY updated_at DESC, id DESC
                 LIMIT ? OFFSET ?""",
            (*params, bounded_limit + 1, bounded_offset),
        ).fetchall()
    has_more = len(rows) > bounded_limit
    items = [_asset_public(row) for row in rows[:bounded_limit]]
    return envelope(
        True,
        "Đã tải Asset Vault Web.",
        data={
            "items": items,
            "state": selected_state,
            "has_more": has_more,
            "next_offset": bounded_offset + len(items) if has_more else None,
            "filters": {
                "q": needle,
                "state": selected_state,
                "project_id": scoped_project_id,
                "reference_kind": selected_reference_kind,
            },
            "pagination": {"limit": bounded_limit, "offset": bounded_offset, "returned": len(items)},
        },
    )


@router.get("/{asset_id}/lifecycle")
async def get_asset_lifecycle(asset_id: str, account: dict = Depends(require_account)):
    """Inspect the current retained lifecycle without exposing blob internals.

    There is intentionally no fabricated timeline: this is a current-state
    inspection endpoint backed by the canonical Asset Vault metadata and its
    owner-scoped retained-reference summary.
    """
    _require_enabled()
    asset_id = _validate_id(asset_id, label="Asset Vault ID")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = _row_for_account(conn, asset_id, str(account["id"]))
        if not row:
            return _asset_not_found()
        lifecycle = _lifecycle_public(
            row,
            reference_summary=_lifecycle_reference_summary(
                conn,
                asset_id=asset_id,
                account_id=str(account["id"]),
            ),
        )
    return envelope(True, "Đã tải vòng đời Asset Vault.", data={"lifecycle": lifecycle})


@router.get("/{asset_id}/preview")
async def preview_asset_video(
    asset_id: str,
    request: Request,
    account: dict = Depends(require_account),
):
    """Return one sealed private MP4/WebM for the current browser session.

    The endpoint is intentionally not a generic media proxy: it accepts no
    remote URL, has no signed/public URL, rejects byte ranges, does no codec
    probing or transcoding and never changes an asset, job, provider, wallet
    or payment state.  The Portal converts the verified same-origin response
    to an in-memory Blob and revokes that Blob URL when the session view ends.
    """

    _require_enabled()
    if not asset_vault_video_preview_enabled():
        raise HTTPException(status_code=503, detail="Xem trước video private chưa được bật cho môi trường này")
    if request.headers.get("range"):
        # A future seeking/range implementation needs its own verified media
        # delivery review.  Reject early so neither a database lookup nor a
        # private blob hash becomes an oracle/amplification path.
        raise HTTPException(status_code=416, detail="Xem trước video private không hỗ trợ byte range")

    asset_id = _validate_id(asset_id, label="Asset Vault ID")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with transaction() as conn:
        row = _row_for_account(conn, asset_id, account_id)
    if not row or str(row[7]) != ACTIVE_STATE or not _video_preview_source_allowed(row):
        # Keep inactive, foreign and non-previewable sources indistinguishable
        # from a missing asset.  The browser receives no path/hash/provider or
        # codec detail that could turn private storage into an enumeration API.
        return _asset_not_found()

    byte_size = int(row[6])
    stream = open_verified_private_asset_stream(
        storage_key=str(row[12]),
        expected_bytes=byte_size,
        expected_digest=str(row[11]),
    )
    if stream is None:
        _mark_unavailable(asset_id, account_id)
        return _asset_unavailable()
    sealed_stream = seal_verified_private_file(
        stream,
        expected_bytes=byte_size,
        expected_digest=str(row[11]),
    )
    if sealed_stream is None:
        _mark_unavailable(asset_id, account_id)
        return _asset_unavailable()

    try:
        with transaction() as conn:
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="web.asset_vault.video_preview",
                request_id=_request_id(request),
                target=asset_id,
                detail=f"format={str(row[4]).lstrip('.').lower()};bytes={byte_size};delivery=inline_no_range",
            )
    except Exception:
        sealed_stream.close()
        raise
    return private_asset_inline_response(
        sealed_stream,
        byte_size=byte_size,
        media_type=str(row[5]),
        filename=str(row[3]),
    )


@router.get("/{asset_id}")
async def get_asset(asset_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    asset_id = _validate_id(asset_id, label="Asset Vault ID")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = _row_for_account(conn, asset_id, str(account["id"]))
    if not row or str(row[7]) not in VISIBLE_STATES:
        return _asset_not_found()
    return envelope(True, "Đã tải thông tin tệp Web.", data={"asset": _visible_asset(row)})


@router.post("/upload")
async def upload_asset(
    request: Request,
    file: Annotated[UploadFile, File(description="Tệp riêng tư cho Web Asset Vault")],
    display_name: Annotated[str, Form()] = "",
    project_id: Annotated[str, Form()] = "",
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    account: dict = Depends(require_csrf),
):
    _require_enabled()
    key = _idempotency_key(idempotency_key)
    original_filename, extension = _safe_filename(file.filename)
    safe_display_name = _safe_display_name(display_name, source_name=original_filename)
    canonical_media_type = _canonical_media_type(extension, file.content_type)
    scoped_project_id = _validate_id(project_id, label="Project ID") if str(project_id or "").strip() else None
    root = asset_vault_directory()
    temporary = _staging_path(root)
    scope = f"web.asset_vault.upload:{account['id']}"
    marker = ""
    final_path: Path | None = None
    try:
        byte_size, content_digest, prefix = await _stream_upload(file, temporary)
        _validate_content(temporary, extension, prefix)
        request_fingerprint = _fingerprint(
            file_digest=content_digest,
            display_name=safe_display_name,
            original_filename=original_filename,
            project_id=scoped_project_id,
        )
        reservation, cached, marker = _reserve_idempotency(scope, key, request_fingerprint)
        if reservation == "cached" and cached is not None:
            return cached
        if reservation == "pending":
            raise HTTPException(status_code=409, detail="Tệp với idempotency key này đang được xử lý")

        asset_id = str(uuid.uuid4())
        storage_key = f"objects/{uuid.uuid4().hex}.blob"
        final_path = _storage_path(root, storage_key)
        _private_asset_vault_child_directory(root, "objects")
        os.replace(temporary, final_path)

        with transaction() as conn:
            _ensure_project_scope(conn, project_id=scoped_project_id, account_id=str(account["id"]))
            if not _quota_available(conn, str(account["id"]), byte_size):
                raise HTTPException(status_code=413, detail="Asset Vault đã đạt quota của Web account")
            now = utc_now()
            conn.execute(
                """INSERT INTO web_asset_files
                   (id, account_id, project_id, display_name, original_filename, extension, content_type,
                    byte_size, sha256, storage_key, state, created_at, updated_at, archived_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
                (
                    asset_id, str(account["id"]), scoped_project_id, safe_display_name, original_filename,
                    extension, canonical_media_type, byte_size, content_digest, storage_key, ACTIVE_STATE, now, now,
                ),
            )
            response = envelope(
                True,
                "Đã lưu tệp vào Asset Vault Web.",
                data={
                    "asset": {
                        "id": asset_id,
                        "project_id": scoped_project_id,
                        "display_name": safe_display_name,
                        "original_filename": original_filename,
                        "extension": extension,
                        "content_type": canonical_media_type,
                        "byte_size": byte_size,
                        "state": ACTIVE_STATE,
                        "created_at": now,
                        "updated_at": now,
                        "archived_at": None,
                    }
                },
            )
            _record_audit(
                conn,
                account_id=str(account["id"]),
                canonical_user_id=None,
                action="web.asset_vault.upload",
                request_id=_request_id(request),
                target=asset_id,
                detail=f"bytes={byte_size};mime={canonical_media_type}",
            )
            _store_response(
                conn,
                scope=scope,
                key=key,
                marker=marker,
                fingerprint=request_fingerprint,
                response=response,
            )
        return response
    except Exception:
        if final_path is not None:
            _safe_unlink(final_path)
        if marker:
            _release_idempotency(scope, key, marker)
        raise
    finally:
        _safe_unlink(temporary)


@router.get("/{asset_id}/download")
async def download_asset(asset_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    asset_id = _validate_id(asset_id, label="Asset Vault ID")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = _row_for_account(conn, asset_id, str(account["id"]))
    if not row or str(row[7]) != ACTIVE_STATE:
        return _asset_not_found()
    root = asset_vault_directory()
    try:
        private_path = _storage_path(root, str(row[12]))
    except RuntimeError:
        _mark_unavailable(asset_id, str(account["id"]))
        return _asset_unavailable()
    stream = _open_verified_private_file(
        private_path,
        expected_bytes=int(row[6]),
        expected_digest=str(row[11]),
    )
    if stream is None:
        _mark_unavailable(asset_id, str(account["id"]))
        return _asset_unavailable()
    sealed_stream = seal_verified_private_file(
        stream,
        expected_bytes=int(row[6]),
        expected_digest=str(row[11]),
    )
    if sealed_stream is None:
        _mark_unavailable(asset_id, str(account["id"]))
        return _asset_unavailable()
    return private_asset_attachment_response(
        sealed_stream,
        byte_size=int(row[6]),
        media_type=str(row[5]),
        filename=str(row[3]),
    )


@router.post("/{asset_id}/restore")
async def restore_asset(
    asset_id: str,
    payload: AssetRestoreRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Restore only a verified archived blob for its signed owner.

    The integrity check intentionally happens before the state becomes active.
    A missing, malformed, symlinked, size-mismatched or digest-mismatched blob
    is fail-closed as ``unavailable`` and cannot be revived by a retry.
    """
    _require_enabled()
    asset_id = _validate_id(asset_id, label="Asset Vault ID")
    account_id = str(account["id"])
    expected_revision = int(payload.expected_revision)
    key = _idempotency_key(payload.idempotency_key)
    scope = f"web.asset_vault.restore:{account_id}:{asset_id}"
    fingerprint = hashlib.sha256(
        f"restore:{asset_id}:{expected_revision}".encode("utf-8")
    ).hexdigest()
    reservation, cached, marker = _reserve_idempotency(scope, key, fingerprint)
    if reservation == "cached" and cached is not None:
        return cached
    if reservation == "pending":
        raise HTTPException(status_code=409, detail="Yêu cầu khôi phục tệp đang được xử lý")

    verified_stream: BinaryIO | None = None
    try:
        # Do not hold a SQLite write transaction while hashing a private blob.
        # The second transaction rechecks the state and revision, so this gap
        # cannot reactivate an asset that was changed after inspection.
        with transaction() as conn:
            row = _row_for_account(conn, asset_id, account_id)
            if not row or str(row[7]) != ARCHIVED_STATE:
                response = _asset_not_found()
                _store_response(conn, scope=scope, key=key, marker=marker, fingerprint=fingerprint, response=response)
                return response
            if _lifecycle_revision(row) != expected_revision:
                response = _asset_lifecycle_conflict()
                _record_audit(
                    conn,
                    account_id=account_id,
                    canonical_user_id=None,
                    action="web.asset_vault.restore",
                    request_id=_request_id(request),
                    outcome="guarded",
                )
                _store_response(conn, scope=scope, key=key, marker=marker, fingerprint=fingerprint, response=response)
                return response

        private_path: Path | None = None
        try:
            private_path = _storage_path(asset_vault_directory(), str(row[12]))
            verified_stream = _open_verified_private_file(
                private_path,
                expected_bytes=int(row[6]),
                expected_digest=str(row[11]),
            )
        except (OSError, RuntimeError):
            verified_stream = None

        with transaction() as conn:
            latest = _row_for_account(conn, asset_id, account_id)
            if not latest or str(latest[7]) != ARCHIVED_STATE:
                response = _asset_not_found()
            elif _lifecycle_revision(latest) != expected_revision:
                response = _asset_lifecycle_conflict()
                _record_audit(
                    conn,
                    account_id=account_id,
                    canonical_user_id=None,
                    action="web.asset_vault.restore",
                    request_id=_request_id(request),
                    outcome="guarded",
                )
            # Keep the descriptor opened, compare it to the current entry and
            # rehash that same descriptor immediately before activation. This
            # closes the prior verify-by-path → activate window; later
            # downloads independently pin and hash again before streaming.
            elif (
                verified_stream is None
                or private_path is None
                or not _pinned_private_file_is_current(verified_stream, private_path)
                or not _verify_pinned_private_file(
                    verified_stream,
                    expected_bytes=int(latest[6]),
                    expected_digest=str(latest[11]),
                )
            ):
                now = utc_now()
                next_revision = _lifecycle_revision(latest) + 1
                updated = conn.execute(
                    """UPDATE web_asset_files
                       SET state=?, updated_at=?, lifecycle_revision=lifecycle_revision + 1
                       WHERE id=? AND account_id=? AND state=? AND lifecycle_revision=?""",
                    (
                        UNAVAILABLE_STATE,
                        now,
                        asset_id,
                        account_id,
                        ARCHIVED_STATE,
                        expected_revision,
                    ),
                )
                if updated.rowcount != 1:
                    response = _asset_lifecycle_conflict()
                else:
                    unavailable_row = _row_with_lifecycle_state(
                        latest,
                        state=UNAVAILABLE_STATE,
                        updated_at=now,
                        archived_at=str(latest[10]) if latest[10] else None,
                        lifecycle_revision=next_revision,
                    )
                    response = _asset_restore_unavailable()
                    response["data"] = {
                        "lifecycle": _lifecycle_public(
                            unavailable_row,
                            reference_summary=_lifecycle_reference_summary(
                                conn,
                                asset_id=asset_id,
                                account_id=account_id,
                            ),
                        )
                    }
                    _record_audit(
                        conn,
                        account_id=account_id,
                        canonical_user_id=None,
                        action="web.asset_vault.restore",
                        request_id=_request_id(request),
                        outcome="guarded",
                    )
            else:
                now = utc_now()
                next_revision = _lifecycle_revision(latest) + 1
                updated = conn.execute(
                    """UPDATE web_asset_files
                       SET state=?, archived_at=NULL, updated_at=?, lifecycle_revision=lifecycle_revision + 1
                       WHERE id=? AND account_id=? AND state=? AND lifecycle_revision=?""",
                    (
                        ACTIVE_STATE,
                        now,
                        asset_id,
                        account_id,
                        ARCHIVED_STATE,
                        expected_revision,
                    ),
                )
                if updated.rowcount != 1:
                    response = _asset_lifecycle_conflict()
                else:
                    restored_row = _row_with_lifecycle_state(
                        latest,
                        state=ACTIVE_STATE,
                        updated_at=now,
                        archived_at=None,
                        lifecycle_revision=next_revision,
                    )
                    response = envelope(
                        True,
                        "Đã khôi phục tệp vào Asset Vault đang hoạt động.",
                        data={
                            "asset": _visible_asset(restored_row),
                            "lifecycle": _lifecycle_public(
                                restored_row,
                                reference_summary=_lifecycle_reference_summary(
                                    conn,
                                    asset_id=asset_id,
                                    account_id=account_id,
                                ),
                            ),
                        },
                    )
                    _record_audit(
                        conn,
                        account_id=account_id,
                        canonical_user_id=None,
                        action="web.asset_vault.restore",
                        request_id=_request_id(request),
                    )
            _store_response(conn, scope=scope, key=key, marker=marker, fingerprint=fingerprint, response=response)
        return response
    except Exception:
        _release_idempotency(scope, key, marker)
        raise
    finally:
        if verified_stream is not None:
            try:
                verified_stream.close()
            except OSError:
                pass


@router.post("/{asset_id}/archive")
async def archive_asset(
    asset_id: str,
    payload: AssetArchiveRequest,
    request: Request,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    account: dict = Depends(require_csrf),
):
    _require_enabled()
    asset_id = _validate_id(asset_id, label="Asset Vault ID")
    account_id = str(account["id"])
    expected_revision = int(payload.expected_revision)
    key = _idempotency_key(idempotency_key)
    scope = f"web.asset_vault.archive:{account_id}:{asset_id}"
    fingerprint = hashlib.sha256(f"archive:{asset_id}:{expected_revision}".encode("utf-8")).hexdigest()
    reservation, cached, marker = _reserve_idempotency(scope, key, fingerprint)
    if reservation == "cached" and cached is not None:
        return cached
    if reservation == "pending":
        raise HTTPException(status_code=409, detail="Yêu cầu lưu trữ tệp đang được xử lý")
    try:
        with transaction() as conn:
            row = _row_for_account(conn, asset_id, account_id)
            if not row or str(row[7]) != ACTIVE_STATE:
                response = _asset_not_found()
            elif _lifecycle_revision(row) != expected_revision:
                response = _asset_lifecycle_conflict()
                _record_audit(
                    conn,
                    account_id=account_id,
                    canonical_user_id=None,
                    action="web.asset_vault.archive",
                    request_id=_request_id(request),
                    outcome="guarded",
                )
            else:
                now = utc_now()
                next_revision = _lifecycle_revision(row) + 1
                updated = conn.execute(
                    """UPDATE web_asset_files
                        SET state=?, archived_at=?, updated_at=?, lifecycle_revision=lifecycle_revision + 1
                        WHERE id=? AND account_id=? AND state=? AND lifecycle_revision=?""",
                    (ARCHIVED_STATE, now, now, asset_id, account_id, ACTIVE_STATE, expected_revision),
                )
                if updated.rowcount != 1:
                    response = _asset_lifecycle_conflict()
                else:
                    archived_row = _row_with_lifecycle_state(
                        row,
                        state=ARCHIVED_STATE,
                        updated_at=now,
                        archived_at=now,
                        lifecycle_revision=next_revision,
                    )
                    public = _visible_asset(archived_row)
                    response = envelope(True, "Đã lưu trữ tệp khỏi Asset Vault đang hoạt động.", data={"asset": public})
                    _record_audit(
                        conn,
                        account_id=account_id,
                        canonical_user_id=None,
                        action="web.asset_vault.archive",
                        request_id=_request_id(request),
                        target=asset_id,
                        detail="state=archived",
                    )
            _store_response(conn, scope=scope, key=key, marker=marker, fingerprint=fingerprint, response=response)
        return response
    except Exception:
        _release_idempotency(scope, key, marker)
        raise
