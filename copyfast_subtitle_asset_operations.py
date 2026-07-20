"""Bounded private SRT/VTT validation and conversion from Asset Vault.

This module is intentionally a small Web-native execution boundary.  It reads
only an active, owner-scoped subtitle file through the Asset Vault's pinned
stream helper, validates a portable SRT/VTT subset, and can create a separate
private conversion artifact.  It does not read a browser path/URL/text body,
call a Bot/provider, perform ASR/translation/dubbing, run FFmpeg, or touch
wallet, Xu, PayOS, webhooks or Telegram state.
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
from typing import Any, BinaryIO
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator
from starlette.concurrency import run_in_threadpool

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_assets import (
    open_verified_private_asset_stream,
    private_asset_attachment_response,
    seal_verified_private_file,
)
from copyfast_db import (
    asset_vault_enabled,
    ensure_copyfast_schema,
    subtitle_asset_operations_directory,
    subtitle_asset_operations_enabled,
    transaction,
    utc_now,
)
from copyfast_subtitle_format_core import (
    MAX_INPUT_BYTES,
    MAX_OUTPUT_BYTES,
    SUPPORTED_FORMATS,
    SubtitleFormatError,
    cues_digest,
    decode_subtitle_bytes,
    parse_subtitle_text,
    render_subtitle_text,
)


router = APIRouter(prefix="/api/v1/subtitle-asset-operations", tags=["Web Subtitle Asset Operations"])

SUBTITLE_VALIDATE_KIND = "subtitle_validate"
SUBTITLE_CONVERT_KIND = "subtitle_convert"
SUPPORTED_KINDS = frozenset({SUBTITLE_VALIDATE_KIND, SUBTITLE_CONVERT_KIND})
OPERATION_STATES = frozenset({"queued", "processing", "completed", "failed", "guarded", "unavailable"})
MIME_BY_FORMAT = {"srt": "application/x-subrip", "vtt": "text/vtt"}
EXTENSION_BY_FORMAT = {"srt": ".srt", "vtt": ".vtt"}
FILENAME_BY_FORMAT = {"srt": "toan-aas-subtitle.srt", "vtt": "toan-aas-subtitle.vtt"}

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
ASSET_STORAGE_KEY_PATTERN = re.compile(r"^objects/[0-9a-f]{32}\.blob$")
OUTPUT_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.(?P<suffix>srt|vtt)$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

CHUNK_BYTES = 64 * 1024
ORPHAN_RETENTION_SECONDS = 60 * 60
SUBTITLE_TOPOLOGY_SQLITE_SINGLE_REPLICA = "sqlite_single_replica"
REPLICA_COUNT_ENV_NAMES = ("RAILWAY_REPLICA_COUNT", "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT")

# Keep raw fields required for lifecycle/integrity checks in one stable order.
# `_operation_public` deliberately does not return source identifiers, hashes,
# storage keys, filenames supplied by a user, or failure internals.
OPERATION_SELECT = """id, source_asset_id, project_id, kind, target_format, state,
                      source_sha256, source_byte_size, source_lifecycle_revision,
                      source_format, cue_count, timed_duration_ms, semantic_sha256,
                      storage_key, original_filename, content_type, byte_size, sha256,
                      failure_code, created_at, queued_at, started_at, completed_at, updated_at"""


class SubtitleAssetOperationError(Exception):
    """A known safe operation failure without private parser/storage details."""

    def __init__(self, message: str, *, code: str = "SUBTITLE_OPERATION_INVALID"):
        super().__init__(message)
        self.public_message = message
        self.code = code


class _BaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SubtitleAssetValidateRequest(_BaseRequest):
    source_asset_id: StrictStr = Field(min_length=36, max_length=36)
    idempotency_key: StrictStr = Field(min_length=12, max_length=160)

    @field_validator("source_asset_id")
    @classmethod
    def valid_source_asset_id(cls, value: StrictStr) -> str:
        return _uuid(value, label="Asset Vault ID")

    @field_validator("idempotency_key")
    @classmethod
    def valid_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(value)


class SubtitleAssetConvertRequest(SubtitleAssetValidateRequest):
    target_format: StrictStr = Field(min_length=3, max_length=3)

    @field_validator("target_format")
    @classmethod
    def valid_target_format(cls, value: StrictStr) -> str:
        candidate = str(value or "").strip().lower()
        if candidate not in SUPPORTED_FORMATS:
            raise ValueError("Định dạng đích chỉ nhận srt hoặc vtt")
        return candidate


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


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


def _require_enabled() -> None:
    if not subtitle_asset_operations_enabled() or not asset_vault_enabled():
        raise HTTPException(
            status_code=503,
            detail="Subtitle Asset Operations cần Asset Vault private và storage đầu ra riêng đã được bật",
        )
    topology_code = _topology_guarded_code()
    if topology_code:
        raise HTTPException(
            status_code=503,
            detail="Subtitle Asset Operations chỉ chạy trên topology SQLite single-replica đã được xác nhận.",
        )


def _topology_guarded_code() -> str | None:
    """Fail closed rather than running local SQLite execution on many replicas."""

    topology = os.environ.get("WEBAPP_SUBTITLE_ASSET_OPERATIONS_TOPOLOGY", "").strip().lower()
    if topology != SUBTITLE_TOPOLOGY_SQLITE_SINGLE_REPLICA:
        return "SUBTITLE_TOPOLOGY_UNVERIFIED"
    attested = False
    for name in REPLICA_COUNT_ENV_NAMES:
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        attested = True
        try:
            replicas = int(raw)
        except ValueError:
            return "SUBTITLE_REPLICA_COUNT_UNVERIFIED"
        if replicas != 1:
            return "SUBTITLE_MULTI_REPLICA_BLOCKED"
    return None if attested else "SUBTITLE_REPLICA_COUNT_UNVERIFIED"


def ensure_subtitle_asset_operations_runtime() -> None:
    """Validate the explicit single-process contract during enabled startup."""

    if not subtitle_asset_operations_enabled():
        return
    if not asset_vault_enabled():
        raise RuntimeError("Subtitle Asset Operations cần WEBAPP_ASSET_VAULT_ENABLED=true")
    if _topology_guarded_code():
        raise RuntimeError("Subtitle Asset Operations cần topology SQLite single-replica đã được xác nhận")


def _maximum_account_bytes() -> int:
    raw = os.environ.get("WEBAPP_SUBTITLE_ASSET_OPERATIONS_QUOTA_KB", "1024").strip()
    try:
        kibibytes = int(raw)
    except ValueError:
        kibibytes = 1024
    # A single verified output is <= 96 KiB.  Avoid a typo enabling an
    # unbounded customer artifact collection while retaining a useful local
    # quota for a conversion-only helper.
    return max(96, min(kibibytes, 10_240)) * 1024


def _private_directory(root: Path, name: str) -> Path:
    if name not in {".staging", "outputs"}:
        raise RuntimeError("Thư mục Subtitle Asset Operation không hợp lệ")
    private_root = root.resolve()
    candidate = private_root / name
    if candidate.exists() and candidate.is_symlink():
        raise RuntimeError("Thư mục Subtitle Asset Operation không được là symbolic link")
    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise RuntimeError("Thư mục Subtitle Asset Operation không hợp lệ")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError("Thư mục Subtitle Asset Operation vượt ngoài storage riêng") from exc
    return resolved


def _staging_path(root: Path, suffix: str) -> Path:
    return _private_directory(root, ".staging") / f"{uuid.uuid4().hex}{suffix}"


def _output_path(root: Path, storage_key: str, *, expected_format: str | None = None) -> Path:
    match = OUTPUT_STORAGE_KEY_PATTERN.fullmatch(str(storage_key or ""))
    if not match or (expected_format is not None and match.group("suffix") != expected_format):
        raise RuntimeError("Storage key Subtitle Asset Operation không hợp lệ")
    private_root = root.resolve()
    candidate = private_root / storage_key
    try:
        candidate.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError("Storage key Subtitle Asset Operation vượt ngoài storage riêng") from exc
    return candidate


def _safe_unlink(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.is_file() and not path.is_symlink():
            path.unlink()
    except OSError:
        pass


def _same_private_file(left: os.stat_result, right: os.stat_result) -> bool:
    return left.st_dev == right.st_dev and left.st_ino == right.st_ino


def _private_directory_fd_supported() -> bool:
    supported = getattr(os, "supports_dir_fd", set())
    return bool(
        getattr(os, "O_DIRECTORY", 0)
        and getattr(os, "O_NOFOLLOW", 0)
        and os.open in supported
        and os.stat in supported
        and os.replace in supported
    )


def _open_private_outputs_directory(path: Path) -> tuple[int, int] | None:
    if not _private_directory_fd_supported():
        return None
    root_descriptor = -1
    outputs_descriptor = -1
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_BINARY", 0)
        root_descriptor = os.open(path.parent.parent, flags)
        outputs_descriptor = os.open("outputs", flags, dir_fd=root_descriptor)
        return root_descriptor, outputs_descriptor
    except OSError:
        if outputs_descriptor >= 0:
            os.close(outputs_descriptor)
        if root_descriptor >= 0:
            os.close(root_descriptor)
        return None


def _close_private_outputs_directory(descriptors: tuple[int, int] | None) -> None:
    if descriptors is None:
        return
    for descriptor in reversed(descriptors):
        try:
            os.close(descriptor)
        except OSError:
            pass


def _safe_unlink_private_output(path: Path | None) -> None:
    if path is None:
        return
    descriptors = _open_private_outputs_directory(path) if _private_directory_fd_supported() else None
    if descriptors is not None:
        _root_descriptor, outputs_descriptor = descriptors
        try:
            os.unlink(path.name, dir_fd=outputs_descriptor)
        except OSError:
            pass
        finally:
            _close_private_outputs_directory(descriptors)
        return
    try:
        parent_metadata = os.lstat(path.parent)
        leaf_metadata = os.lstat(path)
        if (
            not stat.S_ISDIR(parent_metadata.st_mode)
            or stat.S_ISLNK(parent_metadata.st_mode)
            or not (stat.S_ISREG(leaf_metadata.st_mode) or stat.S_ISLNK(leaf_metadata.st_mode))
        ):
            return
        path.unlink()
    except OSError:
        pass


def _publish_into_private_outputs(staged: Path, final_path: Path) -> None:
    """Atomically move one checked server-generated file into private outputs."""

    if not staged.is_file() or staged.is_symlink():
        raise SubtitleAssetOperationError("Output subtitle không còn sẵn sàng", code="SUBTITLE_OUTPUT_INVALID")
    descriptors = _open_private_outputs_directory(final_path) if _private_directory_fd_supported() else None
    if _private_directory_fd_supported() and descriptors is None:
        raise SubtitleAssetOperationError("Không thể khóa storage subtitle riêng tư", code="SUBTITLE_OUTPUT_INVALID")
    if descriptors is not None:
        _root_descriptor, outputs_descriptor = descriptors
        try:
            try:
                os.stat(final_path.name, dir_fd=outputs_descriptor, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise SubtitleAssetOperationError("Không thể chuẩn bị output subtitle riêng tư", code="SUBTITLE_OUTPUT_INVALID")
            os.replace(staged, final_path.name, dst_dir_fd=outputs_descriptor)
            return
        except SubtitleAssetOperationError:
            raise
        except OSError as exc:
            raise SubtitleAssetOperationError("Không thể chuẩn bị output subtitle riêng tư", code="SUBTITLE_OUTPUT_INVALID") from exc
        finally:
            _close_private_outputs_directory(descriptors)
    parent_metadata = os.lstat(final_path.parent)
    if not stat.S_ISDIR(parent_metadata.st_mode) or stat.S_ISLNK(parent_metadata.st_mode):
        raise SubtitleAssetOperationError("Không thể khóa storage subtitle riêng tư", code="SUBTITLE_OUTPUT_INVALID")
    if final_path.exists() or final_path.is_symlink():
        raise SubtitleAssetOperationError("Không thể chuẩn bị output subtitle riêng tư", code="SUBTITLE_OUTPUT_INVALID")
    try:
        os.replace(staged, final_path)
    except OSError as exc:
        raise SubtitleAssetOperationError("Không thể chuẩn bị output subtitle riêng tư", code="SUBTITLE_OUTPUT_INVALID") from exc


def _source_format(extension: Any, content_type: Any) -> str | None:
    normalized_extension = str(extension or "").strip().lower()
    normalized_type = str(content_type or "").strip().lower()
    for fmt, suffix in EXTENSION_BY_FORMAT.items():
        if normalized_extension == suffix and normalized_type == MIME_BY_FORMAT[fmt]:
            return fmt
    return None


def _owner_source(conn: Any, *, account_id: str, source_asset_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """SELECT id, project_id, extension, content_type, byte_size, sha256, storage_key, lifecycle_revision
             FROM web_asset_files
            WHERE id=? AND account_id=? AND state='active'""",
        (source_asset_id, account_id),
    ).fetchone()
    if not row:
        return None
    fmt = _source_format(row[2], row[3])
    byte_size = _safe_int(row[4])
    digest = str(row[5] or "").lower()
    lifecycle_revision = _safe_int(row[7])
    storage_key = str(row[6] or "")
    if (
        fmt is None
        or byte_size is None
        or byte_size < 1
        or byte_size > MAX_INPUT_BYTES
        or lifecycle_revision is None
        or lifecycle_revision < 1
        or not SHA256_PATTERN.fullmatch(digest)
        or not ASSET_STORAGE_KEY_PATTERN.fullmatch(storage_key)
    ):
        return None
    return {
        "asset_id": str(row[0]),
        "project_id": str(row[1]) if row[1] else None,
        "format": fmt,
        "byte_size": byte_size,
        "sha256": digest,
        "storage_key": storage_key,
        "lifecycle_revision": lifecycle_revision,
    }


def _request_fingerprint(*, kind: str, source: dict[str, Any], target_format: str | None) -> str:
    payload = json.dumps(
        {
            "kind": kind,
            "source_asset_id": str(source["asset_id"]),
            "source_sha256": str(source["sha256"]),
            "source_byte_size": int(source["byte_size"]),
            "source_lifecycle_revision": int(source["lifecycle_revision"]),
            "source_format": str(source["format"]),
            "target_format": target_format or "",
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _record_event(conn: Any, *, operation_id: str, state: str, when: str | None = None) -> None:
    if state not in OPERATION_STATES:
        raise RuntimeError("Trạng thái Subtitle Asset Operation không hợp lệ")
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 FROM web_subtitle_asset_operation_events WHERE operation_id=?",
        (operation_id,),
    ).fetchone()
    sequence = int(row[0] or 1) if row else 1
    conn.execute(
        """INSERT INTO web_subtitle_asset_operation_events (id, operation_id, state, sequence, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), operation_id, state, sequence, when or utc_now()),
    )


def _operation_row(conn: Any, *, operation_id: str, account_id: str):
    return conn.execute(
        f"SELECT {OPERATION_SELECT} FROM web_subtitle_asset_operations WHERE id=? AND account_id=?",
        (operation_id, account_id),
    ).fetchone()


def _operation_public(row: tuple[Any, ...]) -> dict[str, Any]:
    (
        operation_id, _source_asset_id, _project_id, kind, target_format, state,
        _source_sha256, _source_byte_size, _source_lifecycle_revision,
        source_format, cue_count, timed_duration_ms, semantic_sha256,
        storage_key, _original_filename, content_type, byte_size, sha256,
        _failure_code, created_at, queued_at, started_at, completed_at, updated_at,
    ) = row
    normalized_kind = str(kind or "")
    normalized_target = str(target_format or "")
    completed = str(state or "") == "completed"
    canonical_output = (
        normalized_kind == SUBTITLE_CONVERT_KIND
        and normalized_target in SUPPORTED_FORMATS
        and completed
        and OUTPUT_STORAGE_KEY_PATTERN.fullmatch(str(storage_key or "")) is not None
        and str(storage_key or "").endswith(EXTENSION_BY_FORMAT[normalized_target])
        and str(content_type or "") == MIME_BY_FORMAT[normalized_target]
        and isinstance(byte_size, int)
        and 0 < byte_size <= MAX_OUTPUT_BYTES
        and SHA256_PATTERN.fullmatch(str(sha256 or "").lower()) is not None
        and SHA256_PATTERN.fullmatch(str(semantic_sha256 or "").lower()) is not None
    )
    return {
        "id": str(operation_id),
        "kind": normalized_kind,
        "state": str(state or "guarded"),
        "status": str(state or "guarded"),
        "source_format": str(source_format or "") if str(source_format or "") in SUPPORTED_FORMATS else None,
        "target_format": normalized_target if normalized_target in SUPPORTED_FORMATS else None,
        "cue_count": _safe_int(cue_count),
        "timed_duration_ms": _safe_int(timed_duration_ms),
        "output_available": canonical_output,
        "filename": FILENAME_BY_FORMAT[normalized_target] if canonical_output else None,
        "content_type": MIME_BY_FORMAT[normalized_target] if canonical_output else None,
        "byte_size": int(byte_size) if canonical_output else None,
        "created_at": str(created_at or ""),
        "queued_at": str(queued_at or ""),
        "started_at": str(started_at) if started_at else None,
        "completed_at": str(completed_at) if completed_at else None,
        "updated_at": str(updated_at or ""),
    }


def _operation_public_with_verified_output(row: tuple[Any, ...]) -> dict[str, Any]:
    """Avoid advertising a private download based on database shape alone.

    Conversion outputs are at most 96 KiB, so a descriptor-pinned integrity
    recheck on an owner list/detail response is cheap and avoids a completed
    row becoming a fake "ready" indicator after a volume loss or local tamper.
    It does not mutate state here; download/reconciliation own the durable
    unavailable transition and audit path.
    """

    operation = _operation_public(row)
    if not operation["output_available"]:
        return operation
    if verified_subtitle_asset_output_available(
        target_format=row[4],
        storage_key=row[13],
        content_type=row[15],
        byte_size=row[16],
        digest=row[17],
        semantic=row[12],
    ):
        return operation
    operation["output_available"] = False
    operation["filename"] = None
    operation["content_type"] = None
    operation["byte_size"] = None
    return operation


def verified_subtitle_asset_output_available(
    *,
    target_format: Any,
    storage_key: Any,
    content_type: Any,
    byte_size: Any,
    digest: Any,
    semantic: Any,
) -> bool:
    """Revalidate one bounded output before any read model advertises it.

    This helper deliberately has no database mutation. Direct download and
    startup reconciliation own the durable ``unavailable`` transition; Jobs
    and Assets use the same descriptor/hash/semantic gate to avoid publishing
    a stale ready/download signal between those checks.
    """

    normalized_format = str(target_format or "")
    normalized_bytes = _safe_int(byte_size)
    if (
        normalized_format not in SUPPORTED_FORMATS
        or str(content_type or "") != MIME_BY_FORMAT[normalized_format]
        or normalized_bytes is None
        or normalized_bytes < 1
        or normalized_bytes > MAX_OUTPUT_BYTES
    ):
        return False
    try:
        path = _output_path(
            subtitle_asset_operations_directory(),
            str(storage_key or ""),
            expected_format=normalized_format,
        )
        stream = _open_verified_output(
            path,
            expected_bytes=normalized_bytes,
            expected_digest=str(digest or ""),
            expected_format=normalized_format,
            expected_semantic=str(semantic or ""),
        )
    except (OSError, RuntimeError, ValueError):
        return False
    if stream is None:
        return False
    stream.close()
    return True


def _operation_envelope(operation: dict[str, Any], *, replay: bool = False) -> dict[str, Any]:
    state = str(operation.get("state") or "guarded")
    kind = str(operation.get("kind") or "")
    if state == "completed" and kind == SUBTITLE_VALIDATE_KIND:
        return envelope(
            True,
            "Đã kiểm định subtitle private. Thao tác này không tạo file đầu ra.",
            data={"operation": operation, "replay": replay},
            status_name="completed",
        )
    if state == "completed" and kind == SUBTITLE_CONVERT_KIND and operation.get("output_available") is True:
        return envelope(
            True,
            "Đã chuyển đổi subtitle private và xác minh output.",
            data={"operation": operation, "replay": replay},
            status_name="completed",
        )
    if state == "completed" and kind == SUBTITLE_CONVERT_KIND:
        # A completion row is not a delivery claim. A descriptor/hash/semantic
        # recheck can invalidate the private output between execution and the
        # response (for example volume loss or tamper). Fail closed instead of
        # returning a success envelope or saying that a file was verified.
        return envelope(
            False,
            "Output subtitle private chưa qua xác minh để phát an toàn.",
            data={"operation": operation, "replay": replay},
            status_name="unavailable",
            error_code="WEB_SUBTITLE_ASSET_OUTPUT_UNAVAILABLE",
        )
    if state in {"queued", "processing"}:
        return envelope(
            False,
            "Subtitle private đang xử lý; chưa có output để tải trước khi xác minh.",
            data={"operation": operation, "replay": replay},
            status_name=state,
            error_code="WEB_SUBTITLE_ASSET_OPERATION_PENDING",
        )
    return envelope(
        False,
        "Không thể xử lý subtitle private an toàn.",
        data={"operation": operation, "replay": replay},
        status_name=state if state in OPERATION_STATES else "guarded",
        error_code="WEB_SUBTITLE_ASSET_OPERATION_FAILED",
    )


def _read_verified_source(source: dict[str, Any]) -> tuple[str, tuple[Any, ...], str, int, int]:
    """Read a small pinned Asset Vault stream and return only verified semantics."""

    stream = open_verified_private_asset_stream(
        storage_key=str(source["storage_key"]),
        expected_bytes=int(source["byte_size"]),
        expected_digest=str(source["sha256"]),
    )
    if stream is None:
        raise SubtitleAssetOperationError("Subtitle nguồn không còn integrity để xử lý", code="SUBTITLE_SOURCE_UNAVAILABLE")
    chunks: list[bytes] = []
    digest = hashlib.sha256()
    total = 0
    try:
        with stream:
            while True:
                chunk = stream.read(CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_INPUT_BYTES:
                    raise SubtitleAssetOperationError("Tệp subtitle vượt giới hạn 96 KiB", code="SUBTITLE_INPUT_TOO_LARGE")
                digest.update(chunk)
                chunks.append(chunk)
    except SubtitleAssetOperationError:
        raise
    except OSError as exc:
        raise SubtitleAssetOperationError("Không thể đọc subtitle nguồn riêng tư", code="SUBTITLE_SOURCE_UNAVAILABLE") from exc
    content = b"".join(chunks)
    if (
        total != int(source["byte_size"])
        or not hmac.compare_digest(digest.hexdigest(), str(source["sha256"]))
    ):
        raise SubtitleAssetOperationError("Subtitle nguồn không vượt qua kiểm tra integrity", code="SUBTITLE_SOURCE_UNAVAILABLE")
    try:
        text = decode_subtitle_bytes(content)
        cues = parse_subtitle_text(str(source["format"]), text)
    except SubtitleFormatError as exc:
        raise SubtitleAssetOperationError(exc.args[0] if exc.args else "Subtitle nguồn không hợp lệ", code="SUBTITLE_FORMAT_INVALID") from exc
    semantic = cues_digest(cues)
    duration = max(cue.end_ms for cue in cues)
    return text, cues, semantic, len(cues), duration


def _verify_subtitle_stream(
    stream: BinaryIO,
    *,
    expected_bytes: int,
    expected_digest: str,
    expected_format: str,
    expected_semantic: str,
) -> tuple[int, int]:
    """Verify the exact persistent/delivery descriptor as a strict subtitle."""

    if (
        expected_bytes < 1
        or expected_bytes > MAX_OUTPUT_BYTES
        or expected_format not in SUPPORTED_FORMATS
        or not SHA256_PATTERN.fullmatch(str(expected_digest or "").lower())
        or not SHA256_PATTERN.fullmatch(str(expected_semantic or "").lower())
    ):
        raise SubtitleAssetOperationError("Output subtitle không hợp lệ", code="SUBTITLE_OUTPUT_INVALID")
    try:
        stream.seek(0)
        content = stream.read(expected_bytes + 1)
    except (OSError, ValueError) as exc:
        raise SubtitleAssetOperationError("Output subtitle không còn sẵn sàng", code="SUBTITLE_OUTPUT_INVALID") from exc
    if len(content) != expected_bytes or not hmac.compare_digest(hashlib.sha256(content).hexdigest(), expected_digest):
        raise SubtitleAssetOperationError("Output subtitle không vượt qua kiểm tra integrity", code="SUBTITLE_OUTPUT_INVALID")
    try:
        cues = parse_subtitle_text(expected_format, decode_subtitle_bytes(content))
    except SubtitleFormatError as exc:
        raise SubtitleAssetOperationError("Output subtitle không hợp lệ", code="SUBTITLE_OUTPUT_INVALID") from exc
    if not hmac.compare_digest(cues_digest(cues), expected_semantic):
        raise SubtitleAssetOperationError("Output subtitle không vượt qua kiểm tra semantic", code="SUBTITLE_OUTPUT_INVALID")
    stream.seek(0)
    return len(cues), max(cue.end_ms for cue in cues)


def _write_and_publish_output(
    *,
    root: Path,
    target_format: str,
    output_text: str,
    expected_semantic: str,
) -> tuple[Path, str, int, str, int, int]:
    """Write, parse, atomically publish, then descriptor-verify one output."""

    if target_format not in SUPPORTED_FORMATS:
        raise SubtitleAssetOperationError("Định dạng output subtitle không hợp lệ", code="SUBTITLE_OUTPUT_INVALID")
    encoded = output_text.encode("utf-8")
    if not encoded or len(encoded) > MAX_OUTPUT_BYTES:
        raise SubtitleAssetOperationError("Output subtitle vượt giới hạn 96 KiB", code="SUBTITLE_OUTPUT_LIMIT")
    staging: Path | None = None
    final_path: Path | None = None
    try:
        staging = _staging_path(root, f".{target_format}.tmp")
        try:
            with staging.open("xb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            raise SubtitleAssetOperationError("Không thể chuẩn bị output subtitle riêng tư", code="SUBTITLE_OUTPUT_INVALID") from exc
        output_digest = hashlib.sha256(encoded).hexdigest()
        with staging.open("rb") as stream:
            cue_count, duration = _verify_subtitle_stream(
                stream,
                expected_bytes=len(encoded),
                expected_digest=output_digest,
                expected_format=target_format,
                expected_semantic=expected_semantic,
            )
        storage_key = f"outputs/{uuid.uuid4().hex}.{target_format}"
        _private_directory(root, "outputs")
        final_path = _output_path(root, storage_key, expected_format=target_format)
        _publish_into_private_outputs(staging, final_path)
        staging = None
        persistent = _open_verified_output(
            final_path,
            expected_bytes=len(encoded),
            expected_digest=output_digest,
            expected_format=target_format,
            expected_semantic=expected_semantic,
        )
        if persistent is None:
            raise SubtitleAssetOperationError("Output subtitle không vượt qua kiểm tra integrity", code="SUBTITLE_OUTPUT_INVALID")
        try:
            checked_count, checked_duration = _verify_subtitle_stream(
                persistent,
                expected_bytes=len(encoded),
                expected_digest=output_digest,
                expected_format=target_format,
                expected_semantic=expected_semantic,
            )
        finally:
            persistent.close()
        if (checked_count, checked_duration) != (cue_count, duration):
            raise SubtitleAssetOperationError("Output subtitle không vượt qua kiểm tra semantic", code="SUBTITLE_OUTPUT_INVALID")
        accepted = final_path
        final_path = None
        return accepted, storage_key, len(encoded), output_digest, cue_count, duration
    except Exception:
        _safe_unlink_private_output(final_path)
        raise
    finally:
        _safe_unlink(staging)


def _open_verified_output(
    path: Path,
    *,
    expected_bytes: int,
    expected_digest: str,
    expected_format: str,
    expected_semantic: str,
) -> BinaryIO | None:
    if (
        expected_bytes < 1
        or expected_bytes > MAX_OUTPUT_BYTES
        or expected_format not in SUPPORTED_FORMATS
        or not SHA256_PATTERN.fullmatch(str(expected_digest or "").lower())
        or not SHA256_PATTERN.fullmatch(str(expected_semantic or "").lower())
    ):
        return None
    descriptor = -1
    stream: BinaryIO | None = None
    try:
        directories = _open_private_outputs_directory(path) if _private_directory_fd_supported() else None
        if _private_directory_fd_supported() and directories is None:
            return None
        if directories is not None:
            _root_descriptor, outputs_descriptor = directories
            try:
                before = os.stat(path.name, dir_fd=outputs_descriptor, follow_symlinks=False)
                flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_BINARY", 0)
                descriptor = os.open(path.name, flags, dir_fd=outputs_descriptor)
            finally:
                _close_private_outputs_directory(directories)
        else:
            parent_metadata = os.lstat(path.parent)
            before = os.lstat(path)
            if (
                stat.S_ISLNK(parent_metadata.st_mode)
                or not stat.S_ISDIR(parent_metadata.st_mode)
                or stat.S_ISLNK(before.st_mode)
            ):
                return None
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0))
        pinned = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or not stat.S_ISREG(pinned.st_mode)
            or int(pinned.st_size) != expected_bytes
            or not _same_private_file(before, pinned)
        ):
            return None
        stream = os.fdopen(descriptor, "rb", closefd=True)
        descriptor = -1
        _verify_subtitle_stream(
            stream,
            expected_bytes=expected_bytes,
            expected_digest=expected_digest,
            expected_format=expected_format,
            expected_semantic=expected_semantic,
        )
        accepted = stream
        stream = None
        return accepted
    except (OSError, SubtitleAssetOperationError, ValueError):
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


def _seal_verified_output_for_delivery(
    stream: BinaryIO,
    *,
    expected_bytes: int,
    expected_digest: str,
    expected_format: str,
    expected_semantic: str,
) -> BinaryIO | None:
    sealed = seal_verified_private_file(
        stream,
        expected_bytes=expected_bytes,
        expected_digest=expected_digest,
    )
    if sealed is None:
        return None
    try:
        _verify_subtitle_stream(
            sealed,
            expected_bytes=expected_bytes,
            expected_digest=expected_digest,
            expected_format=expected_format,
            expected_semantic=expected_semantic,
        )
        return sealed
    except SubtitleAssetOperationError:
        sealed.close()
        return None


def _source_still_current(conn: Any, *, account_id: str, source: dict[str, Any]) -> bool:
    row = conn.execute(
        """SELECT state, extension, content_type, byte_size, sha256, storage_key, lifecycle_revision
             FROM web_asset_files WHERE id=? AND account_id=?""",
        (str(source["asset_id"]), account_id),
    ).fetchone()
    return bool(
        row
        and str(row[0]) == "active"
        and _source_format(row[1], row[2]) == str(source["format"])
        and _safe_int(row[3]) == int(source["byte_size"])
        and hmac.compare_digest(str(row[4] or "").lower(), str(source["sha256"]))
        and hmac.compare_digest(str(row[5] or ""), str(source["storage_key"]))
        and _safe_int(row[6]) == int(source["lifecycle_revision"])
    )


def _quota_available(conn: Any, *, account_id: str, additional_bytes: int) -> bool:
    row = conn.execute(
        """SELECT COALESCE(SUM(byte_size), 0)
             FROM web_subtitle_asset_operations
            WHERE account_id=? AND kind=? AND state='completed' AND byte_size IS NOT NULL""",
        (account_id, SUBTITLE_CONVERT_KIND),
    ).fetchone()
    used = int(row[0] or 0) if row else 0
    return used + additional_bytes <= _maximum_account_bytes()


def _mark_terminal(operation_id: str, account_id: str, *, code: str, request_id: str, state: str = "failed") -> None:
    normalized_state = state if state in {"failed", "guarded"} else "failed"
    now = utc_now()
    with transaction() as conn:
        current = conn.execute(
            "SELECT state FROM web_subtitle_asset_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
        if not current or str(current[0]) not in {"queued", "processing"}:
            return
        conn.execute(
            """UPDATE web_subtitle_asset_operations
                   SET state=?, failure_code=?, updated_at=?
                 WHERE id=? AND account_id=? AND state IN ('queued', 'processing')""",
            (normalized_state, code[:80], now, operation_id, account_id),
        )
        _record_event(conn, operation_id=operation_id, state=normalized_state, when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.subtitle_asset_operation.failed",
            request_id=request_id,
            target=operation_id,
            detail=f"code={code[:80]}",
        )


def _mark_output_unavailable(
    operation_id: str,
    account_id: str,
    *,
    request_id: str = "system:subtitle_asset_storage",
) -> None:
    now = utc_now()
    with transaction() as conn:
        changed = conn.execute(
            """UPDATE web_subtitle_asset_operations
                   SET state='unavailable', failure_code='SUBTITLE_OUTPUT_UNAVAILABLE', updated_at=?
                 WHERE id=? AND account_id=? AND state='completed'""",
            (now, operation_id, account_id),
        ).rowcount
        if changed == 1:
            _record_event(conn, operation_id=operation_id, state="unavailable", when=now)
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="web.subtitle_asset_operation.unavailable",
                request_id=request_id,
                target=operation_id,
                detail="code=SUBTITLE_OUTPUT_UNAVAILABLE",
            )


def _claim_operation(
    operation_id: str,
    account_id: str,
    *,
    request_id: str,
) -> tuple[dict[str, Any], str, str | None] | None:
    """Atomically pin the immutable Asset Vault revision before parsing it."""

    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            """SELECT o.source_asset_id, o.source_sha256, o.source_byte_size,
                      o.source_lifecycle_revision, o.source_format, o.kind, o.target_format,
                      f.project_id, f.extension, f.content_type, f.byte_size, f.sha256,
                      f.storage_key, f.lifecycle_revision
                 FROM web_subtitle_asset_operations o
                 JOIN web_asset_files f ON f.id=o.source_asset_id AND f.account_id=o.account_id
                WHERE o.id=? AND o.account_id=? AND o.state='queued' AND f.state='active'""",
            (operation_id, account_id),
        ).fetchone()
        if not row:
            queued = conn.execute(
                "SELECT state FROM web_subtitle_asset_operations WHERE id=? AND account_id=?",
                (operation_id, account_id),
            ).fetchone()
            if queued and str(queued[0]) == "queued":
                changed = conn.execute(
                    """UPDATE web_subtitle_asset_operations
                           SET state='failed', failure_code='SUBTITLE_SOURCE_UNAVAILABLE', updated_at=?
                         WHERE id=? AND account_id=? AND state='queued'""",
                    (now, operation_id, account_id),
                ).rowcount
                if changed == 1:
                    _record_event(conn, operation_id=operation_id, state="failed", when=now)
                    _record_audit(
                        conn,
                        account_id=account_id,
                        canonical_user_id=None,
                        action="web.subtitle_asset_operation.failed",
                        request_id=request_id,
                        target=operation_id,
                        detail="code=SUBTITLE_SOURCE_UNAVAILABLE",
                    )
            return None
        (
            source_asset_id, snapshot_digest, snapshot_bytes, snapshot_revision,
            snapshot_format, kind, target_format, project_id, extension, content_type,
            byte_size, digest, storage_key, lifecycle_revision,
        ) = tuple(row)
        actual_format = _source_format(extension, content_type)
        source = {
            "asset_id": str(source_asset_id),
            "project_id": str(project_id) if project_id else None,
            "format": actual_format,
            "byte_size": _safe_int(byte_size),
            "sha256": str(digest or "").lower(),
            "storage_key": str(storage_key or ""),
            "lifecycle_revision": _safe_int(lifecycle_revision),
        }
        if (
            actual_format is None
            or str(snapshot_format) != actual_format
            or str(snapshot_digest) != source["sha256"]
            or _safe_int(snapshot_bytes) != source["byte_size"]
            or _safe_int(snapshot_revision) != source["lifecycle_revision"]
            or source["byte_size"] is None
            or source["lifecycle_revision"] is None
            or source["byte_size"] < 1
            or source["byte_size"] > MAX_INPUT_BYTES
            or not SHA256_PATTERN.fullmatch(source["sha256"])
            or not ASSET_STORAGE_KEY_PATTERN.fullmatch(source["storage_key"])
        ):
            changed = conn.execute(
                """UPDATE web_subtitle_asset_operations
                       SET state='failed', failure_code='SUBTITLE_SOURCE_CHANGED', updated_at=?
                     WHERE id=? AND account_id=? AND state='queued'""",
                (now, operation_id, account_id),
            ).rowcount
            if changed == 1:
                _record_event(conn, operation_id=operation_id, state="failed", when=now)
                _record_audit(
                    conn,
                    account_id=account_id,
                    canonical_user_id=None,
                    action="web.subtitle_asset_operation.failed",
                    request_id=request_id,
                    target=operation_id,
                    detail="code=SUBTITLE_SOURCE_CHANGED",
                )
            return None
        changed = conn.execute(
            """UPDATE web_subtitle_asset_operations
                   SET state='processing', started_at=?, updated_at=?
                 WHERE id=? AND account_id=? AND state='queued'""",
            (now, now, operation_id, account_id),
        ).rowcount
        if changed != 1:
            return None
        _record_event(conn, operation_id=operation_id, state="processing", when=now)
        return source, str(kind), str(target_format) if target_format else None


def _complete_validation(
    *,
    operation_id: str,
    account_id: str,
    source: dict[str, Any],
    semantic: str,
    cue_count: int,
    duration: int,
    request_id: str,
) -> bool:
    now = utc_now()
    with transaction() as conn:
        if not _source_still_current(conn, account_id=account_id, source=source):
            _terminal_source_changed_in_transaction(
                conn,
                operation_id=operation_id,
                account_id=account_id,
                now=now,
                request_id=request_id,
            )
            return False
        changed = conn.execute(
            """UPDATE web_subtitle_asset_operations
                   SET state='completed', cue_count=?, timed_duration_ms=?, semantic_sha256=?,
                       completed_at=?, updated_at=?, failure_code=NULL
                 WHERE id=? AND account_id=? AND kind=? AND state='processing'""",
            (cue_count, duration, semantic, now, now, operation_id, account_id, SUBTITLE_VALIDATE_KIND),
        ).rowcount
        if changed != 1:
            return False
        _record_event(conn, operation_id=operation_id, state="completed", when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.subtitle_asset_operation.validated",
            request_id=request_id,
            target=operation_id,
            detail=f"format={source['format']};cues={cue_count};duration_ms={duration}",
        )
    return True


def _terminal_source_changed_in_transaction(
    conn: Any,
    *,
    operation_id: str,
    account_id: str,
    now: str,
    request_id: str,
) -> None:
    changed = conn.execute(
        """UPDATE web_subtitle_asset_operations
               SET state='failed', failure_code='SUBTITLE_SOURCE_CHANGED', updated_at=?
             WHERE id=? AND account_id=? AND state IN ('queued', 'processing')""",
        (now, operation_id, account_id),
    ).rowcount
    if changed == 1:
        _record_event(conn, operation_id=operation_id, state="failed", when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.subtitle_asset_operation.failed",
            request_id=request_id,
            target=operation_id,
            detail="code=SUBTITLE_SOURCE_CHANGED",
        )


def _complete_conversion(
    *,
    operation_id: str,
    account_id: str,
    source: dict[str, Any],
    target_format: str,
    semantic: str,
    cue_count: int,
    duration: int,
    storage_key: str,
    byte_size: int,
    digest: str,
    request_id: str,
) -> bool:
    now = utc_now()
    with transaction() as conn:
        if not _source_still_current(conn, account_id=account_id, source=source):
            _terminal_source_changed_in_transaction(
                conn,
                operation_id=operation_id,
                account_id=account_id,
                now=now,
                request_id=request_id,
            )
            return False
        if not _quota_available(conn, account_id=account_id, additional_bytes=byte_size):
            changed = conn.execute(
                """UPDATE web_subtitle_asset_operations
                       SET state='failed', failure_code='SUBTITLE_OUTPUT_QUOTA', updated_at=?
                     WHERE id=? AND account_id=? AND state='processing'""",
                (now, operation_id, account_id),
            ).rowcount
            if changed == 1:
                _record_event(conn, operation_id=operation_id, state="failed", when=now)
                _record_audit(
                    conn,
                    account_id=account_id,
                    canonical_user_id=None,
                    action="web.subtitle_asset_operation.failed",
                    request_id=request_id,
                    target=operation_id,
                    detail="code=SUBTITLE_OUTPUT_QUOTA",
                )
            return False
        changed = conn.execute(
            """UPDATE web_subtitle_asset_operations
                   SET state='completed', cue_count=?, timed_duration_ms=?, semantic_sha256=?,
                       storage_key=?, original_filename=?, content_type=?, byte_size=?, sha256=?,
                       completed_at=?, updated_at=?, failure_code=NULL
                 WHERE id=? AND account_id=? AND kind=? AND target_format=? AND state='processing'""",
            (
                cue_count, duration, semantic, storage_key, FILENAME_BY_FORMAT[target_format],
                MIME_BY_FORMAT[target_format], byte_size, digest, now, now,
                operation_id, account_id, SUBTITLE_CONVERT_KIND, target_format,
            ),
        ).rowcount
        if changed != 1:
            return False
        _record_event(conn, operation_id=operation_id, state="completed", when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.subtitle_asset_operation.converted",
            request_id=request_id,
            target=operation_id,
            detail=f"target_format={target_format};cues={cue_count};bytes={byte_size}",
        )
    return True


def _current_operation_public(operation_id: str, account_id: str) -> dict[str, Any]:
    with transaction() as conn:
        row = _operation_row(conn, operation_id=operation_id, account_id=account_id)
    return _operation_public_with_verified_output(tuple(row)) if row else {}


def _execute_operation(operation_id: str, account_id: str, *, request_id: str) -> dict[str, Any]:
    """Run one bounded local conversion without holding a SQLite transaction open."""

    final_path: Path | None = None
    try:
        root = subtitle_asset_operations_directory()
        claim = _claim_operation(operation_id, account_id, request_id=request_id)
        if claim is None:
            return _current_operation_public(operation_id, account_id)
        source, kind, target_format = claim
        _text, cues, semantic, cue_count, duration = _read_verified_source(source)
        if kind == SUBTITLE_VALIDATE_KIND:
            _complete_validation(
                operation_id=operation_id,
                account_id=account_id,
                source=source,
                semantic=semantic,
                cue_count=cue_count,
                duration=duration,
                request_id=request_id,
            )
            return _current_operation_public(operation_id, account_id)
        if kind != SUBTITLE_CONVERT_KIND or target_format not in SUPPORTED_FORMATS or target_format == source["format"]:
            raise SubtitleAssetOperationError("Yêu cầu chuyển đổi subtitle không hợp lệ", code="SUBTITLE_OPERATION_INVALID")
        rendered = render_subtitle_text(target_format, cues)
        # The renderer must remain a semantic container conversion, never a
        # hidden caption rewrite. Verify its parser/digest before it reaches disk.
        rendered_cues = parse_subtitle_text(target_format, rendered)
        if not hmac.compare_digest(cues_digest(rendered_cues), semantic):
            raise SubtitleAssetOperationError("Output subtitle không vượt qua kiểm tra semantic", code="SUBTITLE_OUTPUT_INVALID")
        final_path, storage_key, byte_size, digest, output_cues, output_duration = _write_and_publish_output(
            root=root,
            target_format=target_format,
            output_text=rendered,
            expected_semantic=semantic,
        )
        if (output_cues, output_duration) != (cue_count, duration):
            raise SubtitleAssetOperationError("Output subtitle không vượt qua kiểm tra semantic", code="SUBTITLE_OUTPUT_INVALID")
        completed = _complete_conversion(
            operation_id=operation_id,
            account_id=account_id,
            source=source,
            target_format=target_format,
            semantic=semantic,
            cue_count=cue_count,
            duration=duration,
            storage_key=storage_key,
            byte_size=byte_size,
            digest=digest,
            request_id=request_id,
        )
        if not completed:
            _safe_unlink_private_output(final_path)
            final_path = None
        else:
            final_path = None
    except SubtitleAssetOperationError as exc:
        _safe_unlink_private_output(final_path)
        _mark_terminal(operation_id, account_id, code=exc.code, request_id=request_id)
    except Exception:
        _safe_unlink_private_output(final_path)
        _mark_terminal(operation_id, account_id, code="SUBTITLE_OPERATION", request_id=request_id)
    return _current_operation_public(operation_id, account_id)


def _reserve_operation(
    *,
    account_id: str,
    kind: str,
    source_asset_id: str,
    target_format: str | None,
    idempotency_key: str,
    request_id: str,
) -> tuple[dict[str, Any], bool]:
    ensure_copyfast_schema()
    public_row: tuple[Any, ...] | None = None
    replay = False
    with transaction() as conn:
        existing = conn.execute(
            f"SELECT {OPERATION_SELECT} FROM web_subtitle_asset_operations WHERE account_id=? AND kind=? AND idempotency_key=?",
            (account_id, kind, idempotency_key),
        ).fetchone()
        if existing:
            public_row = tuple(existing)
            if (
                not hmac.compare_digest(str(public_row[1] or ""), source_asset_id)
                or not hmac.compare_digest(str(public_row[4] or ""), str(target_format or ""))
            ):
                raise HTTPException(status_code=409, detail="Idempotency key đã dùng cho thao tác subtitle khác")
            replay = True
        else:
            source = _owner_source(conn, account_id=account_id, source_asset_id=source_asset_id)
            if source is None:
                raise HTTPException(
                    status_code=422,
                    detail="Chỉ nhận tệp SRT/VTT Asset Vault đang hoạt động, đúng MIME và giới hạn an toàn",
                )
            if kind == SUBTITLE_CONVERT_KIND and target_format == source["format"]:
                raise HTTPException(status_code=422, detail="Hãy chọn định dạng đích khác định dạng nguồn")
            fingerprint = _request_fingerprint(kind=kind, source=source, target_format=target_format)
            operation_id = str(uuid.uuid4())
            now = utc_now()
            conn.execute(
                """INSERT INTO web_subtitle_asset_operations
                       (id, account_id, source_asset_id, project_id, kind, target_format, state,
                        idempotency_key, request_fingerprint, source_sha256, source_byte_size,
                        source_lifecycle_revision, source_format, created_at, queued_at, updated_at)
                     VALUES (?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    operation_id, account_id, source["asset_id"], source["project_id"], kind, target_format,
                    idempotency_key, fingerprint, source["sha256"], source["byte_size"],
                    source["lifecycle_revision"], source["format"], now, now, now,
                ),
            )
            _record_event(conn, operation_id=operation_id, state="queued", when=now)
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="web.subtitle_asset_operation.queued",
                request_id=request_id,
                target=operation_id,
                detail=f"kind={kind};target_format={target_format or 'none'}",
            )
            row = _operation_row(conn, operation_id=operation_id, account_id=account_id)
            public_row = tuple(row) if row else None
    return _operation_public_with_verified_output(public_row) if public_row else {}, replay


@router.get("")
async def list_subtitle_asset_operations(
    limit: int = Query(default=20, ge=1, le=100),
    account: dict = Depends(require_account),
):
    _require_enabled()
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"SELECT {OPERATION_SELECT} FROM web_subtitle_asset_operations WHERE account_id=? ORDER BY updated_at DESC, id DESC LIMIT ?",
            (str(account["id"]), int(limit)),
        ).fetchall()
    return envelope(
        True,
        "Đã tải lịch sử Subtitle Asset private.",
        data={"operations": [_operation_public_with_verified_output(tuple(row)) for row in rows], "source": "web_native"},
        status_name="read_only",
    )


@router.get("/{operation_id}")
async def get_subtitle_asset_operation(operation_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã Subtitle Asset Operation")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = _operation_row(conn, operation_id=operation_id, account_id=str(account["id"]))
        events = conn.execute(
            """SELECT state, created_at FROM web_subtitle_asset_operation_events
                 WHERE operation_id=? ORDER BY sequence ASC, id ASC LIMIT 20""",
            (operation_id,),
        ).fetchall()
    if not row:
        return envelope(
            False,
            "Không tìm thấy Subtitle Asset Operation thuộc Web account hiện tại.",
            status_name="guarded",
            error_code="WEB_SUBTITLE_ASSET_OPERATION_NOT_FOUND",
        )
    return envelope(
        True,
        "Đã tải trạng thái Subtitle Asset Operation.",
        data={
            "operation": _operation_public_with_verified_output(tuple(row)),
            "events": [{"state": str(event[0]), "created_at": str(event[1])} for event in events],
        },
        status_name=str(row[5]) if str(row[5]) in OPERATION_STATES else "guarded",
    )


@router.post("/validate")
async def validate_subtitle_asset(
    payload: SubtitleAssetValidateRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    _require_enabled()
    operation, replay = _reserve_operation(
        account_id=str(account["id"]),
        kind=SUBTITLE_VALIDATE_KIND,
        source_asset_id=payload.source_asset_id,
        target_format=None,
        idempotency_key=payload.idempotency_key,
        request_id=_request_id(request),
    )
    if replay:
        return _operation_envelope(operation, replay=True)
    completed = await run_in_threadpool(
        _execute_operation,
        str(operation.get("id") or ""),
        str(account["id"]),
        request_id=_request_id(request),
    )
    return _operation_envelope(completed)


@router.post("/convert")
async def convert_subtitle_asset(
    payload: SubtitleAssetConvertRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    _require_enabled()
    operation, replay = _reserve_operation(
        account_id=str(account["id"]),
        kind=SUBTITLE_CONVERT_KIND,
        source_asset_id=payload.source_asset_id,
        target_format=payload.target_format,
        idempotency_key=payload.idempotency_key,
        request_id=_request_id(request),
    )
    if replay:
        return _operation_envelope(operation, replay=True)
    completed = await run_in_threadpool(
        _execute_operation,
        str(operation.get("id") or ""),
        str(account["id"]),
        request_id=_request_id(request),
    )
    return _operation_envelope(completed)


async def download_subtitle_asset_operation(operation_id: str, account: dict):
    """Deliver only a sealed, owner-scoped, revalidated conversion output."""

    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã Subtitle Asset Operation")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            """SELECT kind, state, target_format, storage_key, content_type, byte_size, sha256, semantic_sha256
                 FROM web_subtitle_asset_operations WHERE id=? AND account_id=?""",
            (operation_id, account_id),
        ).fetchone()
    if not row or str(row[0]) != SUBTITLE_CONVERT_KIND or str(row[1]) != "completed":
        return envelope(
            False,
            "Output subtitle private chưa sẵn sàng để tải.",
            status_name="guarded",
            error_code="WEB_SUBTITLE_ASSET_OUTPUT_UNAVAILABLE",
        )
    try:
        target_format = str(row[2] or "")
        storage_key = str(row[3] or "")
        content_type = str(row[4] or "")
        byte_size = int(row[5] or 0)
        digest = str(row[6] or "")
        semantic = str(row[7] or "")
        if target_format not in SUPPORTED_FORMATS or content_type != MIME_BY_FORMAT[target_format]:
            raise RuntimeError("MIME Subtitle Asset Operation không hợp lệ")
        path = _output_path(subtitle_asset_operations_directory(), storage_key, expected_format=target_format)
        stream = _open_verified_output(
            path,
            expected_bytes=byte_size,
            expected_digest=digest,
            expected_format=target_format,
            expected_semantic=semantic,
        )
    except (OSError, RuntimeError, ValueError):
        stream = None
    if stream is None:
        _mark_output_unavailable(operation_id, account_id)
        return envelope(
            False,
            "Output subtitle private không còn integrity để tải.",
            status_name="unavailable",
            error_code="WEB_SUBTITLE_ASSET_OUTPUT_UNAVAILABLE",
        )
    sealed = _seal_verified_output_for_delivery(
        stream,
        expected_bytes=byte_size,
        expected_digest=digest,
        expected_format=target_format,
        expected_semantic=semantic,
    )
    if sealed is None:
        return envelope(
            False,
            "Không thể chuẩn bị output subtitle riêng tư để tải an toàn. Vui lòng thử lại.",
            status_name="guarded",
            error_code="WEB_SUBTITLE_ASSET_DELIVERY_UNAVAILABLE",
        )
    try:
        return private_asset_attachment_response(
            sealed,
            byte_size=byte_size,
            media_type=MIME_BY_FORMAT[target_format],
            filename=FILENAME_BY_FORMAT[target_format],
        )
    except Exception:
        sealed.close()
        raise


@router.get("/{operation_id}/download")
async def download_subtitle_asset_operation_route(operation_id: str, account: dict = Depends(require_account)):
    return await download_subtitle_asset_operation(operation_id, account)


def reconcile_subtitle_asset_operation_storage(*, interrupted_before: str | None = None) -> None:
    """Fail closed for interrupted work, tampered outputs and stale orphans."""

    if not subtitle_asset_operations_enabled():
        return
    ensure_copyfast_schema()
    root = subtitle_asset_operations_directory()
    outputs = _private_directory(root, "outputs")
    staging = _private_directory(root, ".staging")
    cutoff_fence = ""
    if interrupted_before:
        try:
            parsed = datetime.fromisoformat(str(interrupted_before).strip().replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("timezone")
            cutoff_fence = parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
        except ValueError as exc:
            raise RuntimeError("Startup Subtitle Asset Operation reconciliation fence không hợp lệ") from exc
    now = utc_now()
    with transaction() as conn:
        query = "SELECT id, account_id FROM web_subtitle_asset_operations WHERE state IN ('queued', 'processing')"
        params: tuple[Any, ...] = ()
        if cutoff_fence:
            query += " AND COALESCE(started_at, queued_at, created_at, updated_at) < ?"
            params = (cutoff_fence,)
        for operation_id, account_id in conn.execute(query, params).fetchall():
            changed = conn.execute(
                """UPDATE web_subtitle_asset_operations
                       SET state='failed', failure_code='SUBTITLE_OPERATION_INTERRUPTED', updated_at=?
                     WHERE id=? AND account_id=? AND state IN ('queued', 'processing')""",
                (now, str(operation_id), str(account_id)),
            ).rowcount
            if changed == 1:
                _record_event(conn, operation_id=str(operation_id), state="failed", when=now)
                _record_audit(
                    conn,
                    account_id=str(account_id),
                    canonical_user_id=None,
                    action="web.subtitle_asset_operation.failed",
                    request_id="system:subtitle_asset_reconcile",
                    target=str(operation_id),
                    detail="code=SUBTITLE_OPERATION_INTERRUPTED",
                )
        completed = conn.execute(
            """SELECT id, account_id, target_format, storage_key, byte_size, sha256, semantic_sha256
                 FROM web_subtitle_asset_operations
                WHERE kind=? AND state='completed'""",
            (SUBTITLE_CONVERT_KIND,),
        ).fetchall()
    known_storage: set[str] = set()
    for operation_id, account_id, target_format, storage_key, byte_size, digest, semantic in completed:
        valid = False
        try:
            normalized_format = str(target_format or "")
            path = _output_path(root, str(storage_key or ""), expected_format=normalized_format)
            stream = _open_verified_output(
                path,
                expected_bytes=int(byte_size or 0),
                expected_digest=str(digest or ""),
                expected_format=normalized_format,
                expected_semantic=str(semantic or ""),
            )
            if stream is not None:
                stream.close()
                known_storage.add(str(storage_key))
                valid = True
        except (OSError, RuntimeError, ValueError):
            valid = False
        if not valid:
            _mark_output_unavailable(str(operation_id), str(account_id))
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=ORPHAN_RETENTION_SECONDS)
    for directory in (outputs, staging):
        try:
            candidates = list(directory.iterdir())
        except OSError:
            continue
        for candidate in candidates:
            try:
                if not candidate.is_file() or candidate.is_symlink():
                    continue
                if directory == outputs and f"outputs/{candidate.name}" in known_storage:
                    continue
                if datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc) < cutoff:
                    _safe_unlink(candidate)
            except OSError:
                continue
