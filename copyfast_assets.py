"""Private, Web-owned Asset Vault.

The vault is intentionally a small, independent storage product: signed Web
accounts can safely keep files and attach them to Web Projects without using a
browser-supplied filesystem path, public static URL, localStorage identity, or
an external execution service.  This module owns metadata and private blobs
only; it does not represent a generated job result or an account balance.
"""

from __future__ import annotations

import codecs
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import uuid
from typing import Annotated, Any, BinaryIO, Iterator
from urllib.parse import quote
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.background import BackgroundTask

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import (
    asset_vault_directory,
    asset_vault_enabled,
    ensure_copyfast_schema,
    transaction,
    utc_now,
)


router = APIRouter(prefix="/api/v1/asset-vault", tags=["Web Asset Vault"])

ACTIVE_STATE = "active"
ARCHIVED_STATE = "archived"
UNAVAILABLE_STATE = "unavailable"
VISIBLE_STATES = frozenset({ACTIVE_STATE, ARCHIVED_STATE})
ALL_STATES = frozenset({ACTIVE_STATE, ARCHIVED_STATE, UNAVAILABLE_STATE})
REFERENCE_KINDS = frozenset({"all", "pdf", "image"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
ASSET_ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
STORAGE_KEY_PATTERN = re.compile(r"^objects/[0-9a-f]{32}\.blob$")
PENDING_MARKER_KEY = "_web_asset_vault_pending"
PENDING_SECONDS = 5 * 60
ORPHAN_RETENTION_SECONDS = 60 * 60
CHUNK_BYTES = 1024 * 1024
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


def _staging_path(root: Path) -> Path:
    directory = root / ".staging"
    directory.mkdir(parents=True, exist_ok=True)
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


def _quota_available(conn, account_id: str, additional_bytes: int) -> bool:
    # Archive deliberately removes download access but does not erase its
    # private blob. Count every retained row so a customer cannot bypass the
    # storage quota by repeatedly upload → archive cycling.
    row = conn.execute(
        "SELECT COALESCE(SUM(byte_size), 0) FROM web_asset_files WHERE account_id=?",
        (account_id,),
    ).fetchone()
    used = int(row[0] or 0) if row else 0
    return used + additional_bytes <= _maximum_account_bytes()


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
    staging = root / ".staging"
    objects = root / "objects"
    staging.mkdir(parents=True, exist_ok=True)
    objects.mkdir(parents=True, exist_ok=True)
    with transaction() as conn:
        referenced = {str(row[0]) for row in conn.execute("SELECT storage_key FROM web_asset_files").fetchall()}
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
        final_path.parent.mkdir(parents=True, exist_ok=True)
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
