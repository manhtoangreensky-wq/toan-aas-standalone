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
import uuid
from typing import Annotated, Any
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

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
    candidate = (root / storage_key).resolve()
    try:
        candidate.relative_to(root.resolve())
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


def _row_for_account(conn, asset_id: str, account_id: str) -> tuple[Any, ...] | None:
    return conn.execute(
        """SELECT id, project_id, display_name, original_filename, extension, content_type,
                  byte_size, state, created_at, updated_at, archived_at, sha256, storage_key
           FROM web_asset_files WHERE id=? AND account_id=?""",
        (asset_id, account_id),
    ).fetchone()


def _visible_asset(row: tuple[Any, ...]) -> dict[str, Any]:
    return _asset_public(row[:11])


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


def _verify_private_file(path: Path, *, expected_bytes: int, expected_digest: str) -> bool:
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size != expected_bytes:
            return False
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
        return hmac.compare_digest(digest.hexdigest(), expected_digest)
    except OSError:
        return False


def _mark_unavailable(asset_id: str, account_id: str) -> None:
    with transaction() as conn:
        conn.execute(
            """UPDATE web_asset_files SET state=?, updated_at=?
               WHERE id=? AND account_id=? AND state=?""",
            (UNAVAILABLE_STATE, utc_now(), asset_id, account_id, ACTIVE_STATE),
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
    account: dict = Depends(require_account),
):
    _require_enabled()
    selected_state = str(state or ACTIVE_STATE).strip().lower()
    if selected_state not in VISIBLE_STATES:
        raise HTTPException(status_code=422, detail="Bộ lọc trạng thái Asset Vault không hợp lệ")
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            """SELECT id, project_id, display_name, original_filename, extension, content_type,
                      byte_size, state, created_at, updated_at, archived_at
               FROM web_asset_files
               WHERE account_id=? AND state=?
               ORDER BY updated_at DESC, id DESC LIMIT 100""",
            (str(account["id"]), selected_state),
        ).fetchall()
    items = [_asset_public(row) for row in rows]
    return envelope(True, "Đã tải Asset Vault Web.", data={"items": items, "state": selected_state})


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
    if not _verify_private_file(private_path, expected_bytes=int(row[6]), expected_digest=str(row[11])):
        _mark_unavailable(asset_id, str(account["id"]))
        return _asset_unavailable()
    return FileResponse(
        path=private_path,
        media_type=str(row[5]),
        filename=str(row[3]),
        content_disposition_type="attachment",
        headers={
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.post("/{asset_id}/archive")
async def archive_asset(
    asset_id: str,
    request: Request,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    account: dict = Depends(require_csrf),
):
    _require_enabled()
    asset_id = _validate_id(asset_id, label="Asset Vault ID")
    key = _idempotency_key(idempotency_key)
    scope = f"web.asset_vault.archive:{account['id']}:{asset_id}"
    fingerprint = hashlib.sha256(f"archive:{asset_id}".encode("utf-8")).hexdigest()
    reservation, cached, marker = _reserve_idempotency(scope, key, fingerprint)
    if reservation == "cached" and cached is not None:
        return cached
    if reservation == "pending":
        raise HTTPException(status_code=409, detail="Yêu cầu lưu trữ tệp đang được xử lý")
    try:
        with transaction() as conn:
            row = _row_for_account(conn, asset_id, str(account["id"]))
            if not row or str(row[7]) != ACTIVE_STATE:
                response = _asset_not_found()
            else:
                now = utc_now()
                conn.execute(
                    """UPDATE web_asset_files SET state=?, archived_at=?, updated_at=?
                       WHERE id=? AND account_id=? AND state=?""",
                    (ARCHIVED_STATE, now, now, asset_id, str(account["id"]), ACTIVE_STATE),
                )
                public = _visible_asset((*row[:7], ARCHIVED_STATE, row[8], now, now))
                response = envelope(True, "Đã lưu trữ tệp khỏi Asset Vault đang hoạt động.", data={"asset": public})
                _record_audit(
                    conn,
                    account_id=str(account["id"]),
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
