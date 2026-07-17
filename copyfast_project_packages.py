"""Private, immutable Project Package exports owned by the Web App.

Project Packages are deliberately distinct from the Bot's service ``/packages``
catalog, canonical Bot jobs, Bot-delivered assets, and customer-uploaded Asset
Vault files.  A package captures one bounded Web Project snapshot and compiles
it into a private ZIP only after the server has written and verified the
artifact.  No Bot bridge, provider, wallet, PayOS, or browser-side identity is
part of this module.
"""

from __future__ import annotations

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
from typing import Any, BinaryIO, Iterator
from urllib.parse import quote
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from starlette.background import BackgroundTask

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import (
    ensure_copyfast_schema,
    project_package_directory,
    project_package_enabled,
    transaction,
    utc_now,
)


router = APIRouter(prefix="/api/v1", tags=["Web Project Packages"])

PACKAGE_STATES = frozenset({"queued", "processing", "completed", "failed", "unavailable"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
STORAGE_KEY_PATTERN = re.compile(r"^packages/[0-9a-f]{32}\.zip$")
MAX_DOCUMENTS = 100
MAX_ASSET_REFERENCES = 100
ORPHAN_RETENTION_SECONDS = 60 * 60
CHUNK_BYTES = 1024 * 1024
ZIP_TIMESTAMP = (2024, 1, 1, 0, 0, 0)

PACKAGE_SELECT = """id, project_id, state, document_count, asset_reference_count,
                    original_filename, content_type, byte_size, created_at, queued_at,
                    started_at, completed_at, updated_at, failure_code, storage_key,
                    sha256, snapshot_digest"""


class PackageCreateRequest(BaseModel):
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("idempotency_key")
    @classmethod
    def valid_idempotency_key(cls, value: str) -> str:
        return _idempotency_key(value)


def _require_enabled() -> None:
    if not project_package_enabled():
        raise HTTPException(status_code=503, detail="Project Package chưa được bật cho môi trường này")


def _maximum_bytes() -> int:
    raw = os.environ.get("WEBAPP_PROJECT_PACKAGE_MAX_MB", "20").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 20
    return max(1, min(megabytes, 100)) * 1024 * 1024


def _maximum_account_bytes() -> int:
    raw = os.environ.get("WEBAPP_PROJECT_PACKAGE_QUOTA_MB", "100").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 100
    return max(1, min(megabytes, 5_000)) * 1024 * 1024


def _uuid(value: str, *, label: str) -> str:
    candidate = str(value or "").strip()
    if not UUID_PATTERN.fullmatch(candidate):
        raise HTTPException(status_code=422, detail=f"{label} không hợp lệ")
    return str(uuid.UUID(candidate))


def _idempotency_key(value: str | None) -> str:
    key = str(value or "").strip()
    if not IDEMPOTENCY_PATTERN.fullmatch(key):
        raise HTTPException(status_code=422, detail="Idempotency key không hợp lệ")
    return key


def _storage_path(root: Path, storage_key: str) -> Path:
    if not STORAGE_KEY_PATTERN.fullmatch(storage_key):
        raise RuntimeError("Storage key Project Package không hợp lệ")
    candidate = (root / storage_key).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError("Storage key Project Package vượt ngoài thư mục riêng") from exc
    return candidate


def _staging_path(root: Path) -> Path:
    staging = root / ".staging"
    staging.mkdir(parents=True, exist_ok=True)
    return staging / f"{uuid.uuid4().hex}.zip"


def _safe_unlink(path: Path | None) -> None:
    if path is None:
        return
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


def _same_private_file(left: os.stat_result, right: os.stat_result) -> bool:
    """Compare a private blob by physical identity, never by pathname text."""

    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def _private_directory_fd_supported() -> bool:
    """Whether this host can pin Project Package path components by descriptor."""

    supported = getattr(os, "supports_dir_fd", set())
    return bool(
        getattr(os, "O_DIRECTORY", 0)
        and getattr(os, "O_NOFOLLOW", 0)
        and os.open in supported
        and os.stat in supported
    )


def _open_private_package_directory(path: Path) -> tuple[int, int] | None:
    """Pin the package root and `packages/` before opening a final ZIP.

    Railway Linux supports descriptor-relative open/stat.  Pinning the
    intermediate directory eliminates a directory-swap race in addition to a
    final symlink race.  Platforms without that primitive retain a guarded
    fallback below; they never use a verified path as an HTTP response path.
    """

    if not _private_directory_fd_supported():
        return None
    root_descriptor = -1
    packages_descriptor = -1
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_BINARY", 0)
        root_descriptor = os.open(path.parent.parent, directory_flags)
        packages_descriptor = os.open("packages", directory_flags, dir_fd=root_descriptor)
        return root_descriptor, packages_descriptor
    except OSError:
        if packages_descriptor >= 0:
            os.close(packages_descriptor)
        if root_descriptor >= 0:
            os.close(root_descriptor)
        return None


def _close_private_package_directory(descriptors: tuple[int, int] | None) -> None:
    if descriptors is None:
        return
    for descriptor in reversed(descriptors):
        try:
            os.close(descriptor)
        except OSError:
            pass


def _open_verified_private_package_file(path: Path, *, expected_bytes: int, expected_digest: str) -> BinaryIO | None:
    """Open, rehash and pin one package ZIP without a path verify/open race.

    The returned descriptor is the authority.  The caller must not reopen
    `path`: doing so would let an attacker swap a verified pathname before an
    HTTP response starts.  Delivery seals this pinned descriptor again into an
    anonymous temporary file before any bytes leave the process.
    """

    if expected_bytes <= 0 or expected_bytes > _maximum_bytes() or not expected_digest:
        return None
    descriptor = -1
    stream: BinaryIO | None = None
    try:
        directories = _open_private_package_directory(path) if _private_directory_fd_supported() else None
        if _private_directory_fd_supported() and directories is None:
            return None
        if directories is not None:
            _root_descriptor, packages_descriptor = directories
            try:
                before = os.stat(path.name, dir_fd=packages_descriptor, follow_symlinks=False)
                flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_BINARY", 0)
                descriptor = os.open(path.name, flags, dir_fd=packages_descriptor)
            finally:
                _close_private_package_directory(directories)
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
        read_bytes = 0
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            read_bytes += len(chunk)
            digest.update(chunk)
        if read_bytes != expected_bytes or not hmac.compare_digest(digest.hexdigest(), expected_digest):
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


def _seal_verified_private_package_file(
    stream: BinaryIO,
    *,
    expected_bytes: int,
    expected_digest: str,
) -> BinaryIO | None:
    """Copy a pinned verified ZIP into an anonymous, rehashed delivery stream."""

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


def _private_package_chunks(stream: BinaryIO) -> Iterator[bytes]:
    try:
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            yield chunk
    finally:
        stream.close()


def _private_package_attachment_response(stream: BinaryIO, *, byte_size: int, filename: str) -> StreamingResponse:
    """Serve only a sealed package descriptor as a never-cached attachment."""

    if byte_size <= 0:
        stream.close()
        raise ValueError("Kích thước Project Package không hợp lệ")
    safe_name = str(filename or "project-package.zip").replace("\r", " ").replace("\n", " ").strip() or "project-package.zip"
    return StreamingResponse(
        _private_package_chunks(stream),
        media_type="application/zip",
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


def _package_public(row: tuple[Any, ...]) -> dict[str, Any]:
    state = str(row[2])
    byte_size = int(row[7]) if row[7] is not None else None
    return {
        "id": str(row[0]),
        "project_id": str(row[1]),
        "state": state,
        "document_count": int(row[3]),
        "asset_reference_count": int(row[4]),
        "original_filename": str(row[5]) if row[5] else None,
        "content_type": str(row[6]) if row[6] else None,
        "byte_size": byte_size,
        "created_at": str(row[8]),
        "queued_at": str(row[9]),
        "started_at": str(row[10]) if row[10] else None,
        "completed_at": str(row[11]) if row[11] else None,
        "updated_at": str(row[12]),
        # A browser may offer a same-origin attachment only after a verified
        # completed state.  It never receives a storage key, SHA or path.
        "download_ready": state == "completed" and bool(row[14]) and byte_size is not None,
    }


def _package_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy Project Package thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_PROJECT_PACKAGE_NOT_FOUND",
    )


def _package_unavailable() -> dict[str, Any]:
    return envelope(
        False,
        "Project Package không còn sẵn sàng để tải. Hãy tạo package mới hoặc liên hệ hỗ trợ.",
        status_name="guarded",
        error_code="WEB_PROJECT_PACKAGE_UNAVAILABLE",
    )


def _project_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy Project thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_PROJECT_NOT_FOUND",
    )


def _record_event(conn, *, package_id: str, state: str, when: str | None = None) -> None:
    if state not in PACKAGE_STATES:
        raise RuntimeError("Trạng thái Project Package không hợp lệ")
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 FROM web_project_package_events WHERE package_id=?",
        (package_id,),
    ).fetchone()
    sequence = int(row[0] or 1) if row else 1
    conn.execute(
        """INSERT INTO web_project_package_events (id, package_id, state, sequence, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), package_id, state, sequence, when or utc_now()),
    )


def _fingerprint(project_id: str) -> str:
    return hashlib.sha256(f"project-package:v1:{project_id}".encode("utf-8")).hexdigest()


def _snapshot_from_rows(
    project: tuple[Any, ...],
    documents: list[tuple[Any, ...]],
    asset_references: list[tuple[Any, ...]],
) -> dict[str, Any]:
    """Create the only artifact input, without identity or infrastructure data."""
    return {
        "format": "toanaas-project-package/v1",
        "project": {
            "title": str(project[1]),
            "summary": str(project[2]),
            "objective": str(project[3]),
        },
        "documents": [
            {
                "kind": str(item[0]),
                "title": str(item[1]),
                "revision": int(item[2]),
                "content": str(item[3]),
            }
            for item in documents
        ],
        # References are informational only.  The ZIP does not copy source
        # bytes or include IDs, hashes, storage keys, paths or signed links.
        "asset_references": [
            {
                "display_name": str(item[0]),
                "original_filename": str(item[1]),
                "extension": str(item[2]),
                "content_type": str(item[3]),
                "byte_size": int(item[4]),
            }
            for item in asset_references
        ],
    }


def _snapshot_json(snapshot: dict[str, Any]) -> str:
    return json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_snapshot(encoded: str) -> dict[str, Any]:
    try:
        parsed = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("Snapshot Project Package không hợp lệ") from exc
    if not isinstance(parsed, dict) or parsed.get("format") != "toanaas-project-package/v1":
        raise RuntimeError("Snapshot Project Package không hợp lệ")
    project = parsed.get("project")
    documents = parsed.get("documents")
    references = parsed.get("asset_references")
    if not isinstance(project, dict) or not isinstance(documents, list) or not isinstance(references, list):
        raise RuntimeError("Snapshot Project Package không hợp lệ")
    if len(documents) > MAX_DOCUMENTS or len(references) > MAX_ASSET_REFERENCES:
        raise RuntimeError("Snapshot Project Package vượt giới hạn")
    return parsed


def _zip_text(archive: ZipFile, name: str, content: str) -> None:
    entry = ZipInfo(name, date_time=ZIP_TIMESTAMP)
    entry.compress_type = ZIP_DEFLATED
    entry.external_attr = 0o600 << 16
    entry.flag_bits |= 0x800
    archive.writestr(entry, content.encode("utf-8"))


def _manifest(snapshot: dict[str, Any]) -> dict[str, Any]:
    documents = snapshot["documents"]
    document_rows = []
    for index, document in enumerate(documents, start=1):
        kind = re.sub(r"[^a-z0-9_-]+", "-", str(document.get("kind") or "document").lower()).strip("-") or "document"
        document_rows.append(
            {
                "kind": kind,
                "title": str(document.get("title") or "Studio Document"),
                "revision": int(document.get("revision") or 1),
                "path": f"documents/{index:03d}-{kind}.txt",
            }
        )
    return {
        "format": "toanaas-project-package/v1",
        "project": snapshot["project"],
        "documents": document_rows,
        "asset_references": snapshot["asset_references"],
        "notice": "Asset references are metadata only. This package contains no source blobs, storage paths, signed URLs, or account identity.",
    }


def _package_readme(snapshot: dict[str, Any]) -> str:
    project = snapshot["project"]
    return (
        "# TOAN AAS Project Package\n\n"
        "Đây là snapshot Web-native bất biến của Project tại thời điểm xuất.\n"
        "Package không gọi dịch vụ bên ngoài hay tạo một công việc delivery khác.\n"
        "Các tham chiếu Asset Vault chỉ là metadata; nội dung tệp gốc không được sao chép vào ZIP.\n\n"
        f"## Project\n\n{str(project.get('title') or 'Project Web')}\n"
    )


def _build_archive(root: Path, snapshot: dict[str, Any]) -> tuple[Path, Path, str, int, str]:
    """Build, atomically promote and verify one bounded server-created ZIP."""
    temporary = _staging_path(root)
    final_path: Path | None = None
    try:
        manifest = _manifest(snapshot)
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=6, strict_timestamps=True) as archive:
            _zip_text(archive, "README.md", _package_readme(snapshot))
            _zip_text(archive, "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            for document, metadata in zip(snapshot["documents"], manifest["documents"], strict=True):
                _zip_text(archive, str(metadata["path"]), str(document.get("content") or "") + "\n")
        byte_size = temporary.stat().st_size
        if byte_size < 1:
            raise RuntimeError("Project Package không có dữ liệu")
        if byte_size > _maximum_bytes():
            raise HTTPException(status_code=413, detail="Project Package vượt quá giới hạn artifact")
        digest = hashlib.sha256()
        with temporary.open("rb") as stream:
            while True:
                chunk = stream.read(CHUNK_BYTES)
                if not chunk:
                    break
                digest.update(chunk)
        storage_key = f"packages/{uuid.uuid4().hex}.zip"
        final_path = _storage_path(root, storage_key)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        os.replace(temporary, final_path)
        content_digest = digest.hexdigest()
        if not _verify_private_file(final_path, expected_bytes=byte_size, expected_digest=content_digest):
            raise RuntimeError("Không thể xác minh artifact Project Package")
        return temporary, final_path, storage_key, byte_size, content_digest
    except Exception:
        _safe_unlink(final_path)
        raise
    finally:
        _safe_unlink(temporary)


def _quota_available(conn, *, account_id: str, additional_bytes: int) -> bool:
    # Keep all retained metadata in the quota.  A later unavailable artifact
    # is not silently treated as a free storage slot while its record exists.
    row = conn.execute(
        "SELECT COALESCE(SUM(byte_size), 0) FROM web_project_packages WHERE account_id=? AND byte_size IS NOT NULL",
        (account_id,),
    ).fetchone()
    used = int(row[0] or 0) if row else 0
    return used + additional_bytes <= _maximum_account_bytes()


def _public_response(package: dict[str, Any]) -> dict[str, Any]:
    state = str(package.get("state") or "failed")
    if state == "completed":
        return envelope(True, "Đã tạo và xác minh Project Package riêng tư.", data={"package": package}, status_name="completed")
    if state in {"queued", "processing"}:
        return envelope(True, "Project Package đang được máy chủ xử lý.", data={"package": package}, status_name=state)
    return envelope(False, "Project Package chưa thể được tạo an toàn.", data={"package": package}, status_name="failed", error_code="WEB_PROJECT_PACKAGE_FAILED")


def _mark_failed(package_id: str, account_id: str, *, request: Request, failure_code: str) -> None:
    ensure_copyfast_schema()
    now = utc_now()
    with transaction() as conn:
        current = conn.execute(
            "SELECT state FROM web_project_packages WHERE id=? AND account_id=?",
            (package_id, account_id),
        ).fetchone()
        if not current or str(current[0]) in {"completed", "unavailable"}:
            return
        conn.execute(
            """UPDATE web_project_packages SET state='failed', failure_code=?, updated_at=?
               WHERE id=? AND account_id=?""",
            (failure_code, now, package_id, account_id),
        )
        _record_event(conn, package_id=package_id, state="failed", when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.project_package.export_failed",
            request_id=_request_id(request),
            target=package_id,
            outcome="failed",
            detail=f"code={failure_code}",
        )


def _mark_unavailable(package_id: str, account_id: str) -> None:
    ensure_copyfast_schema()
    with transaction() as conn:
        updated = conn.execute(
            """UPDATE web_project_packages SET state='unavailable', updated_at=?
               WHERE id=? AND account_id=? AND state='completed'""",
            (utc_now(), package_id, account_id),
        )
        if updated.rowcount:
            _record_event(conn, package_id=package_id, state="unavailable")


def reconcile_project_package_storage() -> None:
    """Clean only aged, unreferenced generated package files after crashes."""
    if not project_package_enabled():
        return
    ensure_copyfast_schema()
    root = project_package_directory()
    staging = root / ".staging"
    packages = root / "packages"
    staging.mkdir(parents=True, exist_ok=True)
    packages.mkdir(parents=True, exist_ok=True)
    with transaction() as conn:
        referenced = {str(row[0]) for row in conn.execute("SELECT storage_key FROM web_project_packages WHERE storage_key IS NOT NULL").fetchall()}
    cutoff = datetime.now(timezone.utc).timestamp() - ORPHAN_RETENTION_SECONDS
    for directory, match_storage_key in ((staging, False), (packages, True)):
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
            if match_storage_key and relative in referenced:
                continue
            _safe_unlink(candidate)


@router.get("/projects/{project_id}/packages")
async def list_project_packages(
    project_id: str,
    limit: int = 30,
    offset: int = Query(0, ge=0, le=10000),
    account: dict = Depends(require_account),
):
    """List package metadata for one signed owner's Project, including archive history."""
    _require_enabled()
    project_id = _uuid(project_id, label="Mã Project")
    bounded_limit = max(1, min(int(limit), 100))
    ensure_copyfast_schema()
    with transaction() as conn:
        owner = conn.execute("SELECT id FROM web_projects WHERE id=? AND account_id=?", (project_id, str(account["id"]))).fetchone()
        if not owner:
            return _project_not_found()
        rows = conn.execute(
            f"""SELECT {PACKAGE_SELECT} FROM web_project_packages
                WHERE project_id=? AND account_id=? ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (project_id, str(account["id"]), bounded_limit + 1, int(offset)),
        ).fetchall()
    has_more = len(rows) > bounded_limit
    return envelope(
        True,
        "Đã tải lịch sử Project Package.",
        data={
            "items": [_package_public(tuple(row)) for row in rows[:bounded_limit]],
            "project_id": project_id,
            "has_more": has_more,
            "next_offset": int(offset) + bounded_limit if has_more else None,
        },
    )


@router.get("/project-packages")
async def list_all_project_packages(
    limit: int = 50,
    offset: int = Query(0, ge=0, le=10000),
    account: dict = Depends(require_account),
):
    """List only the signed account's Web-native package artifacts."""
    _require_enabled()
    bounded_limit = max(1, min(int(limit), 100))
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT {PACKAGE_SELECT} FROM web_project_packages
                WHERE account_id=? ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (str(account["id"]), bounded_limit + 1, int(offset)),
        ).fetchall()
    has_more = len(rows) > bounded_limit
    return envelope(
        True,
        "Đã tải Project Packages Web.",
        data={
            "items": [_package_public(tuple(row)) for row in rows[:bounded_limit]],
            "has_more": has_more,
            "next_offset": int(offset) + bounded_limit if has_more else None,
        },
    )


@router.post("/projects/{project_id}/packages")
async def create_project_package(
    project_id: str,
    payload: PackageCreateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Capture and compile one verified immutable Project ZIP snapshot."""
    _require_enabled()
    root = project_package_directory()
    project_id = _uuid(project_id, label="Mã Project")
    account_id = str(account["id"])
    request_fingerprint = _fingerprint(project_id)
    package_id = ""
    snapshot: dict[str, Any] | None = None

    ensure_copyfast_schema()
    with transaction() as conn:
        existing = conn.execute(
            f"""SELECT {PACKAGE_SELECT}, request_fingerprint FROM web_project_packages
                WHERE account_id=? AND project_id=? AND idempotency_key=?""",
            (account_id, project_id, payload.idempotency_key),
        ).fetchone()
        if existing:
            stored_fingerprint = str(existing[-1] or "")
            if not hmac.compare_digest(stored_fingerprint, request_fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho Project Package khác")
            return _public_response(_package_public(tuple(existing[:-1])))

        project = conn.execute(
            """SELECT id, title, summary, objective FROM web_projects
               WHERE id=? AND account_id=? AND state='active'""",
            (project_id, account_id),
        ).fetchone()
        if not project:
            return _project_not_found()
        documents = conn.execute(
            """SELECT kind, title, revision, content FROM web_studio_documents
               WHERE project_id=? AND account_id=? AND state='active'
               ORDER BY created_at ASC, id ASC LIMIT ?""",
            (project_id, account_id, MAX_DOCUMENTS + 1),
        ).fetchall()
        if len(documents) > MAX_DOCUMENTS:
            raise HTTPException(status_code=422, detail="Project có quá nhiều Studio Document để xuất an toàn")
        asset_references = conn.execute(
            """SELECT display_name, original_filename, extension, content_type, byte_size
               FROM web_asset_files
               WHERE project_id=? AND account_id=? AND state='active'
               ORDER BY created_at ASC, id ASC LIMIT ?""",
            (project_id, account_id, MAX_ASSET_REFERENCES + 1),
        ).fetchall()
        if len(asset_references) > MAX_ASSET_REFERENCES:
            raise HTTPException(status_code=422, detail="Project có quá nhiều tham chiếu Asset Vault để xuất an toàn")
        snapshot = _snapshot_from_rows(tuple(project), [tuple(row) for row in documents], [tuple(row) for row in asset_references])
        encoded_snapshot = _snapshot_json(snapshot)
        package_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_project_packages
               (id, account_id, project_id, state, idempotency_key, request_fingerprint,
                source_snapshot_json, snapshot_digest, document_count, asset_reference_count,
                created_at, queued_at, started_at, updated_at)
               VALUES (?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                package_id, account_id, project_id, payload.idempotency_key, request_fingerprint,
                encoded_snapshot, hashlib.sha256(encoded_snapshot.encode("utf-8")).hexdigest(), len(documents),
                len(asset_references), now, now, now, now,
            ),
        )
        _record_event(conn, package_id=package_id, state="queued", when=now)
        conn.execute(
            "UPDATE web_project_packages SET state='processing', updated_at=? WHERE id=? AND account_id=?",
            (now, package_id, account_id),
        )
        _record_event(conn, package_id=package_id, state="processing", when=now)

    assert snapshot is not None
    final_path: Path | None = None
    try:
        _temporary, final_path, storage_key, byte_size, digest = _build_archive(root, snapshot)
        filename = f"toan-aas-project-package-{package_id}.zip"
        now = utc_now()
        with transaction() as conn:
            current = conn.execute(
                "SELECT state FROM web_project_packages WHERE id=? AND account_id=? AND project_id=?",
                (package_id, account_id, project_id),
            ).fetchone()
            if not current or str(current[0]) != "processing":
                raise RuntimeError("Project Package không còn ở trạng thái có thể hoàn tất")
            if not _quota_available(conn, account_id=account_id, additional_bytes=byte_size):
                raise HTTPException(status_code=413, detail="Project Package đã đạt quota của Web account")
            conn.execute(
                """UPDATE web_project_packages
                   SET state='completed', storage_key=?, original_filename=?, content_type='application/zip',
                       byte_size=?, sha256=?, completed_at=?, updated_at=?, failure_code=NULL
                   WHERE id=? AND account_id=?""",
                (storage_key, filename, byte_size, digest, now, now, package_id, account_id),
            )
            _record_event(conn, package_id=package_id, state="completed", when=now)
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="web.project_package.export",
                request_id=_request_id(request),
                target=package_id,
                detail=f"documents={len(snapshot['documents'])};references={len(snapshot['asset_references'])};bytes={byte_size}",
            )
            completed = conn.execute(
                f"SELECT {PACKAGE_SELECT} FROM web_project_packages WHERE id=? AND account_id=?",
                (package_id, account_id),
            ).fetchone()
        if not completed:
            raise RuntimeError("Không thể đọc Project Package vừa hoàn tất")
        final_path = None  # Ownership is now in metadata; do not remove it.
        return _public_response(_package_public(tuple(completed)))
    except HTTPException as exc:
        _safe_unlink(final_path)
        _mark_failed(package_id, account_id, request=request, failure_code="PACKAGE_QUOTA" if exc.status_code == 413 else "PACKAGE_BUILD")
        raise
    except Exception as exc:
        _safe_unlink(final_path)
        _mark_failed(package_id, account_id, request=request, failure_code="PACKAGE_BUILD")
        raise HTTPException(status_code=500, detail="Không thể tạo Project Package an toàn") from exc


@router.get("/project-packages/{package_id}/download")
async def download_project_package(package_id: str, account: dict = Depends(require_account)):
    """Deliver one owner-scoped, verified package as a private attachment."""
    _require_enabled()
    package_id = _uuid(package_id, label="Mã Project Package")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            f"SELECT {PACKAGE_SELECT} FROM web_project_packages WHERE id=? AND account_id=?",
            (package_id, account_id),
        ).fetchone()
    if not row or str(row[2]) != "completed":
        return _package_not_found()
    storage_key = str(row[14] or "")
    expected_digest = str(row[15] or "")
    expected_size = int(row[7] or 0)
    try:
        private_path = _storage_path(project_package_directory(), storage_key)
    except RuntimeError:
        _mark_unavailable(package_id, account_id)
        return _package_unavailable()
    pinned = _open_verified_private_package_file(
        private_path,
        expected_bytes=expected_size,
        expected_digest=expected_digest,
    )
    if pinned is None:
        _mark_unavailable(package_id, account_id)
        return _package_unavailable()
    sealed = _seal_verified_private_package_file(
        pinned,
        expected_bytes=expected_size,
        expected_digest=expected_digest,
    )
    if sealed is None:
        _mark_unavailable(package_id, account_id)
        return _package_unavailable()
    return _private_package_attachment_response(
        sealed,
        byte_size=expected_size,
        filename=str(row[5] or "project-package.zip"),
    )


@router.get("/project-packages/{package_id}")
async def get_project_package(package_id: str, account: dict = Depends(require_account)):
    """Read safe package metadata and state history for its signed owner."""
    _require_enabled()
    package_id = _uuid(package_id, label="Mã Project Package")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            f"SELECT {PACKAGE_SELECT} FROM web_project_packages WHERE id=? AND account_id=?",
            (package_id, str(account["id"])),
        ).fetchone()
        # Never even read a package's event stream until the package itself
        # has passed the signed owner's canonical account predicate.
        events = conn.execute(
            """SELECT state, created_at FROM web_project_package_events
               WHERE package_id=? ORDER BY sequence ASC, id ASC LIMIT 20""",
            (package_id,),
        ).fetchall() if row else []
    if not row:
        return _package_not_found()
    return envelope(
        True,
        "Đã tải trạng thái Project Package.",
        data={
            "package": _package_public(tuple(row)),
            "events": [{"state": str(event[0]), "created_at": str(event[1])} for event in events],
        },
        status_name=str(row[2]) if str(row[2]) in PACKAGE_STATES else "guarded",
    )
