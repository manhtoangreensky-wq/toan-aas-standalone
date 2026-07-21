"""Bounded, private Web-native Video Poster operations.

This module intentionally does one useful thing well: it extracts a single
verified JPEG poster from an owner-scoped Asset Vault video.  It is not Video
Studio, a Bot job, a provider adapter, a social publishing pipeline, a wallet
mutation or a PayOS surface.  The browser never supplies a path, FFmpeg
argument, timestamp, filter graph, URL or output location.

The runtime remains false-by-default.  When an operator deliberately enables
it, the server validates a sealed copy with ffprobe, invokes a fixed list-argv
FFmpeg command under a tight timeout, verifies the resulting JPEG, atomically
publishes it to a separate private root, and only then marks the operation
``completed``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import threading
from typing import Any, BinaryIO, Callable, Iterator
from urllib.parse import quote
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_assets import open_verified_private_asset_stream
from copyfast_media_runtime import media_ffmpeg_capacity
from copyfast_db import (
    asset_vault_enabled,
    ensure_copyfast_schema,
    transaction,
    utc_now,
    video_operations_directory,
    video_operations_enabled,
    video_poster_enabled,
)


router = APIRouter(prefix="/api/v1/video-operations", tags=["Web Video Operations"])

VIDEO_POSTER_KIND = "video_poster"
OPERATION_STATES = frozenset({"queued", "processing", "completed", "failed", "guarded", "unavailable"})
POSTER_POSITIONS = frozenset({"start", "middle", "end"})
VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".webm"})
VIDEO_MIME_BY_EXTENSION = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
}
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
ASSET_STORAGE_KEY_PATTERN = re.compile(r"^objects/[0-9a-f]{32}\.blob$")
OUTPUT_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.jpg$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

CHUNK_BYTES = 1024 * 1024
MAX_INPUT_BYTES = 25 * 1024 * 1024
MAX_DURATION_SECONDS = 120.0
MIN_DURATION_SECONDS = 0.2
MAX_SOURCE_DIMENSION = 4_096
MAX_SOURCE_PIXELS = 16 * 1024 * 1024
MAX_SOURCE_ASPECT = 12.0
MAX_OUTPUT_DIMENSION = 1_280
MAX_OUTPUT_PIXELS = 2_000_000
PROBE_TIMEOUT_SECONDS = 6.0
RENDER_TIMEOUT_SECONDS = 15.0
ORPHAN_RETENTION_SECONDS = 60 * 60
# Keep the historic private name for focused Poster tests, but make it the
# process-wide gate shared with every other bounded local FFmpeg feature.
_PROCESS_GATE = media_ffmpeg_capacity()
VIDEO_TOPOLOGY_SQLITE_SINGLE_REPLICA = "sqlite_single_replica"
REPLICA_COUNT_ENV_NAMES = ("RAILWAY_REPLICA_COUNT", "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT")

OPERATION_SELECT = """id, source_asset_id, kind, state, poster_position,
                      source_duration_ms, source_width, source_height,
                      frame_timestamp_ms, output_width, output_height,
                      original_filename, content_type, byte_size, sha256,
                      created_at, queued_at, started_at, completed_at, updated_at"""


class VideoOperationError(Exception):
    """Known safe error that never exposes process output or private paths."""

    def __init__(self, message: str, *, code: str = "VIDEO_OPERATION_INVALID"):
        super().__init__(message)
        self.public_message = message
        self.code = code


class VideoPosterRequest(BaseModel):
    """One immutable private video becomes one private JPEG poster."""

    # Keep this small capability closed: a browser must not be able to smuggle
    # future FFmpeg/provider/path options through a request that the server
    # silently accepts.  Adding an input is therefore an explicit reviewed
    # contract change, not an accidental client-side expansion.
    model_config = ConfigDict(extra="forbid")

    source_asset_id: str = Field(min_length=36, max_length=36)
    poster_position: str = Field(default="middle", min_length=3, max_length=12)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("source_asset_id")
    @classmethod
    def valid_source_asset_id(cls, value: str) -> str:
        return _uuid(value, label="Asset Vault ID")

    @field_validator("poster_position")
    @classmethod
    def valid_poster_position(cls, value: str) -> str:
        candidate = str(value or "").strip().lower()
        if candidate not in POSTER_POSITIONS:
            raise ValueError("Vị trí poster chỉ nhận start, middle hoặc end")
        return candidate

    @field_validator("idempotency_key")
    @classmethod
    def valid_idempotency_key(cls, value: str) -> str:
        return _idempotency_key(value)


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
    if not video_operations_enabled() or not asset_vault_enabled():
        raise HTTPException(
            status_code=503,
            detail="Video Operations cần Asset Vault private và storage đầu ra riêng đã được bật",
        )


def _require_poster_enabled() -> tuple[str, str]:
    _require_enabled()
    if not video_poster_enabled():
        raise HTTPException(
            status_code=503,
            detail="Video Poster Lab chưa được bật; cần WEBAPP_VIDEO_POSTER_ENABLED và runtime đã kiểm định",
        )
    topology_code = _topology_guarded_code()
    if topology_code:
        raise HTTPException(
            status_code=503,
            detail="Video Poster chỉ chạy trên topology SQLite single-replica đã được xác nhận.",
        )
    try:
        return _poster_runtime()
    except VideoOperationError as exc:
        raise HTTPException(status_code=503, detail=exc.public_message) from exc


def _binary_path(environment_name: str, expected_name: str) -> str:
    """Resolve a trusted server binary, never an input-derived executable."""

    configured = os.environ.get(environment_name, "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise VideoOperationError("Runtime Video Poster chưa có binary tuyệt đối đã kiểm định", code="VIDEO_RUNTIME_UNAVAILABLE")
    else:
        discovered = shutil.which(expected_name)
        if not discovered:
            raise VideoOperationError("Runtime Video Poster chưa có FFmpeg/ffprobe", code="VIDEO_RUNTIME_UNAVAILABLE")
        candidate = Path(discovered)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise VideoOperationError("Runtime Video Poster chưa có binary hợp lệ", code="VIDEO_RUNTIME_UNAVAILABLE") from exc
    accepted_names = {expected_name.lower(), f"{expected_name}.exe".lower()}
    if resolved.name.lower() not in accepted_names or not resolved.is_file():
        raise VideoOperationError("Runtime Video Poster chưa có binary hợp lệ", code="VIDEO_RUNTIME_UNAVAILABLE")
    if os.name != "nt" and not os.access(resolved, os.X_OK):
        raise VideoOperationError("Runtime Video Poster chưa có binary có thể chạy", code="VIDEO_RUNTIME_UNAVAILABLE")
    return str(resolved)


def _poster_runtime() -> tuple[str, str]:
    return (
        _binary_path("WEBAPP_VIDEO_FFMPEG_BIN", "ffmpeg"),
        _binary_path("WEBAPP_VIDEO_FFPROBE_BIN", "ffprobe"),
    )


def ensure_video_operations_runtime() -> None:
    """Fail closed at startup only for an explicitly enabled poster runtime."""

    if not video_operations_enabled() or not video_poster_enabled():
        return
    if _topology_guarded_code():
        raise RuntimeError("Video Poster cần topology SQLite single-replica đã được xác nhận")
    _poster_runtime()


def _topology_guarded_code() -> str | None:
    """Block the request-time SQLite executor outside one confirmed replica.

    This module intentionally has no distributed lease or worker.  A future
    shared queue/transactional store will receive a new topology contract;
    it must not silently reuse this in-process gate across replicas.
    """

    topology = os.environ.get("WEBAPP_VIDEO_OPERATIONS_TOPOLOGY", "").strip().lower()
    if topology != VIDEO_TOPOLOGY_SQLITE_SINGLE_REPLICA:
        return "VIDEO_TOPOLOGY_UNVERIFIED"
    attested = False
    for name in REPLICA_COUNT_ENV_NAMES:
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        attested = True
        try:
            replicas = int(raw)
        except ValueError:
            return "VIDEO_REPLICA_COUNT_UNVERIFIED"
        if replicas != 1:
            return "VIDEO_MULTI_REPLICA_BLOCKED"
    # The request-time SQLite executor has no cross-process lease.  A runtime
    # acknowledgement alone cannot establish that this process is unique, so
    # every enabled environment must attest one replica explicitly.
    if not attested:
        return "VIDEO_REPLICA_COUNT_UNVERIFIED"
    return None


def _output_path(root: Path, storage_key: str) -> Path:
    if not OUTPUT_STORAGE_KEY_PATTERN.fullmatch(storage_key):
        raise RuntimeError("Storage key Video Operation không hợp lệ")
    # Preserve the physical final component for O_NOFOLLOW below.  Calling
    # resolve() on the whole path would follow a malicious final symlink
    # before descriptor-pinned verification has a chance to reject it.
    private_root = root.resolve()
    candidate = private_root / storage_key
    try:
        candidate.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError("Storage key Video Operation vượt ngoài storage riêng") from exc
    return candidate


def _maximum_output_bytes() -> int:
    raw = os.environ.get("WEBAPP_VIDEO_OPERATIONS_MAX_OUTPUT_MB", "4").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 4
    return max(1, min(megabytes, 4)) * 1024 * 1024


def _maximum_account_bytes() -> int:
    raw = os.environ.get("WEBAPP_VIDEO_OPERATIONS_QUOTA_MB", "50").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 50
    return max(1, min(megabytes, 500)) * 1024 * 1024


def _private_directory(root: Path, name: str) -> Path:
    if name not in {".staging", "outputs"}:
        raise RuntimeError("Thư mục Video Operation không hợp lệ")
    private_root = root.resolve()
    candidate = private_root / name
    if candidate.exists() and candidate.is_symlink():
        raise RuntimeError("Thư mục Video Operation không được là symbolic link")
    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise RuntimeError("Thư mục Video Operation không hợp lệ")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError("Thư mục Video Operation vượt ngoài storage riêng") from exc
    return resolved


def _staging_path(root: Path, suffix: str) -> Path:
    return _private_directory(root, ".staging") / f"{uuid.uuid4().hex}{suffix}"


def _safe_unlink(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.is_file() and not path.is_symlink():
            path.unlink()
    except OSError:
        pass


def _verify_file(path: Path, *, expected_bytes: int, expected_digest: str) -> bool:
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


def _video_magic_matches(extension: str, prefix: bytes) -> bool:
    if extension in {".mp4", ".mov"}:
        return len(prefix) >= 12 and prefix[4:8] == b"ftyp"
    if extension == ".webm":
        return prefix.startswith(b"\x1a\x45\xdf\xa3")
    return False


def _copy_verified_video_source(
    source_stream: BinaryIO,
    destination: Path,
    *,
    extension: str,
    expected_bytes: int,
    expected_digest: str,
) -> None:
    """Copy and hash an owner-scoped source before a media parser opens it."""

    total = 0
    digest = hashlib.sha256()
    prefix = b""
    try:
        with source_stream, destination.open("xb") as write_stream:
            while True:
                chunk = source_stream.read(CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_INPUT_BYTES:
                    raise VideoOperationError("Video nguồn vượt giới hạn 25 MB", code="VIDEO_INPUT_TOO_LARGE")
                if len(prefix) < 32:
                    prefix += chunk[: 32 - len(prefix)]
                digest.update(chunk)
                write_stream.write(chunk)
            write_stream.flush()
            os.fsync(write_stream.fileno())
    except VideoOperationError:
        _safe_unlink(destination)
        raise
    except OSError as exc:
        _safe_unlink(destination)
        raise VideoOperationError("Không thể chuẩn bị video nguồn riêng tư", code="VIDEO_SOURCE_UNAVAILABLE") from exc
    if (
        total != expected_bytes
        or not hmac.compare_digest(digest.hexdigest(), expected_digest)
        or not _video_magic_matches(extension, prefix)
    ):
        _safe_unlink(destination)
        raise VideoOperationError("Video nguồn không vượt qua kiểm tra integrity", code="VIDEO_SOURCE_UNAVAILABLE")


def _safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and result not in {float("inf"), float("-inf")} else None


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result >= 0 else None


def _probe_video(ffprobe: str, source: Path) -> tuple[float, int, int]:
    """Validate a bounded decodable primary video stream through fixed argv."""

    command = [
        ffprobe,
        "-v", "error",
        "-protocol_whitelist", "file,pipe",
        "-select_streams", "v:0",
        "-show_entries", "format=duration:stream=codec_type,width,height,duration",
        "-of", "json",
        str(source),
    ]
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=PROBE_TIMEOUT_SECONDS,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise VideoOperationError("Kiểm tra video vượt thời gian an toàn", code="VIDEO_PROBE_TIMEOUT") from exc
    except OSError as exc:
        raise VideoOperationError("Không thể khởi động runtime Video Poster", code="VIDEO_RUNTIME_UNAVAILABLE") from exc
    if completed.returncode != 0 or len(completed.stdout) > 16 * 1024:
        raise VideoOperationError("Video không vượt qua kiểm tra định dạng", code="VIDEO_PROBE_INVALID")
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VideoOperationError("Video không vượt qua kiểm tra định dạng", code="VIDEO_PROBE_INVALID") from exc
    streams = payload.get("streams") if isinstance(payload, dict) else None
    stream = streams[0] if isinstance(streams, list) and streams and isinstance(streams[0], dict) else {}
    duration = _safe_float((payload.get("format") if isinstance(payload, dict) else {}).get("duration"))
    if duration is None:
        duration = _safe_float(stream.get("duration"))
    width = _safe_int(stream.get("width"))
    height = _safe_int(stream.get("height"))
    if (
        str(stream.get("codec_type") or "") != "video"
        or duration is None
        or duration < MIN_DURATION_SECONDS
        or duration > MAX_DURATION_SECONDS
        or width is None
        or height is None
        or width < 1
        or height < 1
        or width > MAX_SOURCE_DIMENSION
        or height > MAX_SOURCE_DIMENSION
        or width * height > MAX_SOURCE_PIXELS
        or max(width, height) / min(width, height) > MAX_SOURCE_ASPECT
    ):
        raise VideoOperationError("Video vượt giới hạn Poster Lab an toàn", code="VIDEO_PROBE_LIMIT")
    return duration, width, height


def _poster_timestamp(duration: float, position: str) -> float:
    if position == "start":
        return min(max(0.05, duration / 20), max(0.05, duration - 0.05))
    if position == "end":
        return max(0.05, duration - min(0.5, duration / 4))
    return max(0.05, min(duration - 0.05, duration / 2))


def _render_poster(ffmpeg: str, source: Path, destination: Path, *, timestamp: float) -> None:
    """Run one fixed, non-shell FFmpeg poster extraction command.

    The caller owns the module-wide execution gate across source copy,
    ffprobe and FFmpeg.  Keeping the parser and staging write inside that
    same gate prevents concurrent request bursts from opening multiple media
    parsers or exhausting private disk before FFmpeg itself begins.
    """

    command = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-v", "error",
        "-xerror",
        "-protocol_whitelist", "file,pipe",
        "-ss", f"{timestamp:.3f}",
        "-i", str(source),
        "-map", "0:v:0",
        "-frames:v", "1",
        "-an",
        "-sn",
        "-dn",
        "-vf", "scale=1280:1280:force_original_aspect_ratio=decrease:force_divisible_by=2",
        "-q:v", "3",
        str(destination),
    ]
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=RENDER_TIMEOUT_SECONDS,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise VideoOperationError("Tạo poster vượt thời gian an toàn", code="VIDEO_RENDER_TIMEOUT") from exc
    except OSError as exc:
        raise VideoOperationError("Không thể khởi động runtime Video Poster", code="VIDEO_RUNTIME_UNAVAILABLE") from exc
    if completed.returncode != 0:
        raise VideoOperationError("Không thể tạo poster từ video này", code="VIDEO_RENDER_FAILED")


def _pillow_image():
    try:
        from PIL import Image, ImageFile, UnidentifiedImageError
    except ImportError as exc:  # pragma: no cover - deployment configuration
        raise VideoOperationError("Runtime Video Poster chưa có Pillow an toàn", code="VIDEO_RUNTIME_UNAVAILABLE") from exc
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    return Image, UnidentifiedImageError


def _digest_open_stream(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    stream.seek(0)
    while True:
        chunk = stream.read(CHUNK_BYTES)
        if not chunk:
            break
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest()


def _verify_jpeg_stream(stream: BinaryIO) -> tuple[int, int]:
    Image, UnidentifiedImageError = _pillow_image()
    try:
        stream.seek(0)
        with Image.open(stream) as image:
            image.verify()
        stream.seek(0)
        with Image.open(stream) as image:
            image.load()
            width, height = image.size
            image_format = image.format
        if image_format != "JPEG" or width < 1 or height < 1:
            raise VideoOperationError("Poster đầu ra không hợp lệ", code="VIDEO_OUTPUT_INVALID")
        if (
            width > MAX_OUTPUT_DIMENSION
            or height > MAX_OUTPUT_DIMENSION
            or width * height > MAX_OUTPUT_PIXELS
            or max(width, height) / min(width, height) > MAX_SOURCE_ASPECT
        ):
            raise VideoOperationError("Poster đầu ra vượt giới hạn an toàn", code="VIDEO_OUTPUT_LIMIT")
        return int(width), int(height)
    except VideoOperationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise VideoOperationError("Poster đầu ra không hợp lệ", code="VIDEO_OUTPUT_INVALID") from exc


def _verify_output_jpeg(path: Path) -> tuple[int, str, int, int]:
    try:
        if not path.is_file() or path.is_symlink():
            raise VideoOperationError("Poster đầu ra không còn sẵn sàng", code="VIDEO_OUTPUT_INVALID")
        byte_size = int(path.stat().st_size)
        if byte_size < 1 or byte_size > _maximum_output_bytes():
            raise VideoOperationError("Poster đầu ra vượt giới hạn lưu trữ", code="VIDEO_OUTPUT_LIMIT")
        with path.open("rb") as stream:
            width, height = _verify_jpeg_stream(stream)
            digest = _digest_open_stream(stream)
        return byte_size, digest, width, height
    except VideoOperationError:
        raise
    except OSError as exc:
        raise VideoOperationError("Poster đầu ra không hợp lệ", code="VIDEO_OUTPUT_INVALID") from exc


def _publish_verified_jpeg(root: Path, rendered: Path) -> tuple[Path, str, int, str, int, int]:
    final_path: Path | None = None
    try:
        output_bytes, output_digest, output_width, output_height = _verify_output_jpeg(rendered)
        storage_key = f"outputs/{uuid.uuid4().hex}.jpg"
        # Verify the parent before a writer ever resolves the generated leaf.
        # A pre-existing `outputs` symlink must fail the attempt instead of
        # turning a private poster into a file outside this operation root.
        outputs = _private_directory(root, "outputs")
        final_path = _output_path(root, storage_key)
        if final_path.parent != outputs:
            raise VideoOperationError("Không thể chuẩn bị poster riêng tư", code="VIDEO_OUTPUT_INVALID")
        _publish_into_private_outputs(rendered, final_path)
        if not _verify_file(final_path, expected_bytes=output_bytes, expected_digest=output_digest):
            raise VideoOperationError("Poster đầu ra không vượt qua kiểm tra integrity", code="VIDEO_OUTPUT_INVALID")
        verified_bytes, verified_digest, verified_width, verified_height = _verify_output_jpeg(final_path)
        if (
            verified_bytes != output_bytes
            or not hmac.compare_digest(verified_digest, output_digest)
            or (verified_width, verified_height) != (output_width, output_height)
        ):
            raise VideoOperationError("Poster đầu ra không vượt qua kiểm tra integrity", code="VIDEO_OUTPUT_INVALID")
        return final_path, storage_key, output_bytes, output_digest, output_width, output_height
    except Exception:
        _safe_unlink_private_output(final_path)
        raise


def _record_event(conn: Any, *, operation_id: str, state: str, when: str | None = None) -> None:
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 FROM web_video_operation_events WHERE operation_id=?",
        (operation_id,),
    ).fetchone()
    sequence = int(row[0] or 1) if row else 1
    conn.execute(
        """INSERT INTO web_video_operation_events (id, operation_id, state, sequence, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), operation_id, state, sequence, when or utc_now()),
    )


def _quota_available(conn: Any, *, account_id: str, additional_bytes: int) -> bool:
    row = conn.execute(
        """SELECT COALESCE(SUM(byte_size), 0)
             FROM web_video_operations
            WHERE account_id=? AND state='completed' AND byte_size IS NOT NULL""",
        (account_id,),
    ).fetchone()
    used = int(row[0] or 0) if row else 0
    return used + additional_bytes <= _maximum_account_bytes()


def _operation_public(row: tuple[Any, ...]) -> dict[str, Any]:
    (
        operation_id, source_asset_id, kind, state, poster_position,
        source_duration_ms, source_width, source_height, frame_timestamp_ms,
        output_width, output_height, original_filename, content_type,
        byte_size, sha256, created_at, queued_at, started_at, completed_at,
        updated_at,
    ) = row
    completed = str(state or "") == "completed"
    output_ready = (
        completed
        and isinstance(byte_size, int)
        and byte_size > 0
        and isinstance(sha256, str)
        and bool(SHA256_PATTERN.fullmatch(sha256.lower()))
        and str(content_type or "") == "image/jpeg"
        and int(output_width or 0) > 0
        and int(output_height or 0) > 0
    )
    return {
        "id": str(operation_id),
        "source_asset_id": str(source_asset_id),
        "kind": str(kind),
        "state": str(state),
        "status": str(state),
        "poster_position": str(poster_position),
        "source_duration_ms": _safe_int(source_duration_ms),
        "source_width": _safe_int(source_width),
        "source_height": _safe_int(source_height),
        "frame_timestamp_ms": _safe_int(frame_timestamp_ms),
        "output_width": _safe_int(output_width),
        "output_height": _safe_int(output_height),
        "output_available": output_ready,
        "filename": "toan-aas-video-poster.jpg" if output_ready else None,
        "content_type": "image/jpeg" if output_ready else None,
        "byte_size": int(byte_size) if output_ready else None,
        "created_at": str(created_at or ""),
        "queued_at": str(queued_at or ""),
        "started_at": str(started_at or "") if started_at else None,
        "completed_at": str(completed_at or "") if completed_at else None,
        "updated_at": str(updated_at or ""),
    }


def _operation_row(conn: Any, operation_id: str, account_id: str):
    return conn.execute(
        f"SELECT {OPERATION_SELECT} FROM web_video_operations WHERE id=? AND account_id=?",
        (operation_id, account_id),
    ).fetchone()


def _operation_envelope(operation: dict[str, Any], *, replay: bool = False) -> dict[str, Any]:
    state = str(operation.get("state") or "guarded")
    if state == "completed":
        return envelope(True, "Đã tạo poster video private và xác minh output.", data={"operation": operation, "replay": replay}, status_name="completed")
    if state in {"queued", "processing"}:
        return envelope(False, "Poster video đang xử lý; không có output để tải trước khi xác minh.", data={"operation": operation, "replay": replay}, status_name=state, error_code="VIDEO_OPERATION_PENDING")
    return envelope(False, "Không thể tạo poster video an toàn.", data={"operation": operation, "replay": replay}, status_name=state if state in OPERATION_STATES else "guarded", error_code="VIDEO_OPERATION_FAILED")


def _request_fingerprint(*, source_asset_id: str, source_sha256: str, source_bytes: int, position: str) -> str:
    canonical = json.dumps(
        {
            "kind": VIDEO_POSTER_KIND,
            "position": position,
            "source_asset_id": source_asset_id,
            "source_bytes": source_bytes,
            "source_sha256": source_sha256,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _owner_video_source(conn: Any, *, account_id: str, source_asset_id: str) -> tuple[Any, ...] | None:
    row = conn.execute(
        """SELECT id, extension, content_type, byte_size, sha256, storage_key
             FROM web_asset_files
            WHERE id=? AND account_id=? AND state='active'""",
        (source_asset_id, account_id),
    ).fetchone()
    if not row:
        return None
    extension = str(row[1] or "").lower()
    content_type = str(row[2] or "").lower()
    byte_size = _safe_int(row[3])
    digest = str(row[4] or "").lower()
    storage_key = str(row[5] or "")
    if (
        extension not in VIDEO_EXTENSIONS
        or content_type != VIDEO_MIME_BY_EXTENSION.get(extension)
        or byte_size is None
        or byte_size < 1
        or byte_size > MAX_INPUT_BYTES
        or not SHA256_PATTERN.fullmatch(digest)
        or not ASSET_STORAGE_KEY_PATTERN.fullmatch(storage_key)
    ):
        return None
    return (str(row[0]), extension, content_type, byte_size, digest, storage_key)


def _mark_terminal(
    operation_id: str,
    account_id: str,
    *,
    attempt_id: str | None,
    state: str,
    code: str,
    request_id: str,
) -> None:
    if state not in {"failed", "guarded"}:
        state = "failed"
    now = utc_now()
    with transaction() as conn:
        current = conn.execute(
            "SELECT state FROM web_video_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
        if not current or str(current[0]) not in {"queued", "processing"}:
            return
        conn.execute(
            """UPDATE web_video_operations
                   SET state=?, failure_code=?, updated_at=?, revision=revision + 1
                 WHERE id=? AND account_id=?""",
            (state, code[:80], now, operation_id, account_id),
        )
        if attempt_id:
            conn.execute(
                """UPDATE web_video_operation_attempts
                       SET state=?, completed_at=?, failure_code=?
                     WHERE id=? AND operation_id=? AND account_id=? AND state IN ('claimed', 'running')""",
                (state, now, code[:80], attempt_id, operation_id, account_id),
            )
        _record_event(conn, operation_id=operation_id, state=state, when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.video_operation.video_poster_failed",
            request_id=request_id,
            target=operation_id,
            detail=f"code={code[:80]}",
        )


def _mark_output_unavailable(operation_id: str, account_id: str) -> None:
    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            "SELECT state FROM web_video_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
        if not row or str(row[0]) != "completed":
            return
        conn.execute(
            """UPDATE web_video_operations
                   SET state='unavailable', failure_code='VIDEO_OUTPUT_UNAVAILABLE', updated_at=?, revision=revision + 1
                 WHERE id=? AND account_id=?""",
            (now, operation_id, account_id),
        )
        _record_event(conn, operation_id=operation_id, state="unavailable", when=now)


def _start_attempt(operation_id: str, account_id: str) -> tuple[str, tuple[Any, ...]] | None:
    """Claim one queued operation before a bounded in-request execution."""

    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            """SELECT o.source_asset_id, o.poster_position, o.source_sha256, o.source_byte_size,
                      o.source_extension, o.source_content_type, f.extension, f.content_type,
                      f.byte_size, f.sha256, f.storage_key
                 FROM web_video_operations o
                 JOIN web_asset_files f ON f.id=o.source_asset_id AND f.account_id=o.account_id
                WHERE o.id=? AND o.account_id=? AND o.state='queued' AND f.state='active'""",
            (operation_id, account_id),
        ).fetchone()
        if not row:
            queued = conn.execute(
                "SELECT state FROM web_video_operations WHERE id=? AND account_id=?",
                (operation_id, account_id),
            ).fetchone()
            if queued and str(queued[0]) == "queued":
                changed = conn.execute(
                    """UPDATE web_video_operations
                           SET state='failed', failure_code='VIDEO_SOURCE_UNAVAILABLE',
                               updated_at=?, revision=revision + 1
                         WHERE id=? AND account_id=? AND state='queued'""",
                    (now, operation_id, account_id),
                ).rowcount
                if changed == 1:
                    _record_event(conn, operation_id=operation_id, state="failed", when=now)
            return None
        source_asset_id, position, snapshot_digest, snapshot_bytes, snapshot_extension, snapshot_type, extension, content_type, byte_size, digest, storage_key = tuple(row)
        if (
            str(snapshot_digest) != str(digest)
            or int(snapshot_bytes) != int(byte_size)
            or str(snapshot_extension) != str(extension)
            or str(snapshot_type) != str(content_type)
        ):
            changed = conn.execute(
                """UPDATE web_video_operations
                       SET state='failed', failure_code='VIDEO_SOURCE_CHANGED',
                           updated_at=?, revision=revision + 1
                     WHERE id=? AND account_id=? AND state='queued'""",
                (now, operation_id, account_id),
            ).rowcount
            if changed == 1:
                _record_event(conn, operation_id=operation_id, state="failed", when=now)
            return None
        changed = conn.execute(
            """UPDATE web_video_operations
                   SET state='processing', started_at=?, updated_at=?, revision=revision + 1
                 WHERE id=? AND account_id=? AND state='queued'""",
            (now, now, operation_id, account_id),
        ).rowcount
        if changed != 1:
            return None
        attempt_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO web_video_operation_attempts
                   (id, operation_id, account_id, attempt_no, state, fence_token, started_at)
                 VALUES (?, ?, ?, 1, 'running', ?, ?)""",
            (attempt_id, operation_id, account_id, uuid.uuid4().hex, now),
        )
        _record_event(conn, operation_id=operation_id, state="processing", when=now)
        return attempt_id, (str(source_asset_id), str(position), str(extension), int(byte_size), str(digest), str(storage_key))


def _execute_poster(operation_id: str, account_id: str, *, ffmpeg: str, ffprobe: str, request_id: str) -> dict[str, Any]:
    """Run the fixed local execution and persist only a verified final state."""

    source_copy: Path | None = None
    rendered: Path | None = None
    final_path: Path | None = None
    attempt_id: str | None = None
    execution_acquired = False
    try:
        # The root and claim intentionally live inside terminal handling.  A
        # storage/configuration failure after the row is queued must become a
        # truthful failed operation, never a permanently pending receipt.
        root = video_operations_directory()
        claim = _start_attempt(operation_id, account_id)
        if claim is None:
            with transaction() as conn:
                row = _operation_row(conn, operation_id, account_id)
            return _operation_public(tuple(row)) if row else {}
        attempt_id, source = claim
        execution_acquired = _PROCESS_GATE.acquire(timeout=RENDER_TIMEOUT_SECONDS)
        if not execution_acquired:
            raise VideoOperationError("Video Poster đang bận; hãy thử lại sau", code="VIDEO_RUNTIME_BUSY")
        source_asset_id, position, extension, expected_bytes, expected_digest, storage_key = source
        source_stream = open_verified_private_asset_stream(
            storage_key=storage_key,
            expected_bytes=expected_bytes,
            expected_digest=expected_digest,
        )
        if source_stream is None:
            raise VideoOperationError("Video nguồn không còn integrity để xử lý", code="VIDEO_SOURCE_UNAVAILABLE")
        source_copy = _staging_path(root, extension)
        _copy_verified_video_source(
            source_stream,
            source_copy,
            extension=extension,
            expected_bytes=expected_bytes,
            expected_digest=expected_digest,
        )
        duration, source_width, source_height = _probe_video(ffprobe, source_copy)
        timestamp = _poster_timestamp(duration, position)
        rendered = _staging_path(root, ".poster.jpg")
        _render_poster(ffmpeg, source_copy, rendered, timestamp=timestamp)
        final_path, output_storage_key, output_bytes, output_digest, output_width, output_height = _publish_verified_jpeg(root, rendered)
        rendered = None
        now = utc_now()
        with transaction() as conn:
            current = conn.execute(
                "SELECT state FROM web_video_operations WHERE id=? AND account_id=?",
                (operation_id, account_id),
            ).fetchone()
            if not current or str(current[0]) != "processing":
                raise VideoOperationError("Poster không còn ở trạng thái có thể hoàn tất", code="VIDEO_OPERATION_STALE")
            if not _quota_available(conn, account_id=account_id, additional_bytes=output_bytes):
                raise VideoOperationError("Video Poster đã đạt quota của Web account", code="VIDEO_OUTPUT_QUOTA")
            conn.execute(
                """UPDATE web_video_operations
                       SET state='completed', source_duration_ms=?, source_width=?, source_height=?,
                           frame_timestamp_ms=?, output_width=?, output_height=?, storage_key=?,
                           original_filename='toan-aas-video-poster.jpg', content_type='image/jpeg',
                           byte_size=?, sha256=?, completed_at=?, updated_at=?, failure_code=NULL,
                           revision=revision + 1
                     WHERE id=? AND account_id=?""",
                (
                    round(duration * 1000), source_width, source_height, round(timestamp * 1000),
                    output_width, output_height, output_storage_key, output_bytes, output_digest,
                    now, now, operation_id, account_id,
                ),
            )
            conn.execute(
                """UPDATE web_video_operation_attempts
                       SET state='succeeded', completed_at=?, failure_code=NULL
                     WHERE id=? AND operation_id=? AND account_id=? AND state='running'""",
                (now, attempt_id, operation_id, account_id),
            )
            _record_event(conn, operation_id=operation_id, state="completed", when=now)
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="web.video_operation.video_poster",
                request_id=request_id,
                target=operation_id,
                detail=f"source={source_asset_id};position={position};output={output_width}x{output_height};bytes={output_bytes}",
            )
            completed = _operation_row(conn, operation_id, account_id)
        final_path = None
        if not completed:
            raise RuntimeError("Không thể đọc Video Poster vừa hoàn tất")
        return _operation_public(tuple(completed))
    except VideoOperationError as exc:
        _safe_unlink_private_output(final_path)
        _mark_terminal(operation_id, account_id, attempt_id=attempt_id, state="failed", code=exc.code, request_id=request_id)
    except Exception:
        _safe_unlink_private_output(final_path)
        _mark_terminal(operation_id, account_id, attempt_id=attempt_id, state="failed", code="VIDEO_OPERATION", request_id=request_id)
    finally:
        if execution_acquired:
            _PROCESS_GATE.release()
        _safe_unlink(source_copy)
        _safe_unlink(rendered)
    with transaction() as conn:
        row = _operation_row(conn, operation_id, account_id)
    return _operation_public(tuple(row)) if row else {}


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
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_BINARY", 0)
        root_descriptor = os.open(path.parent.parent, directory_flags)
        outputs_descriptor = os.open("outputs", directory_flags, dir_fd=root_descriptor)
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
    """Best-effort cleanup that never follows an output-parent symlink."""

    if path is None:
        return
    descriptors = _open_private_outputs_directory(path) if _private_directory_fd_supported() else None
    if descriptors is not None:
        _root_descriptor, outputs_descriptor = descriptors
        try:
            # unlink removes a directory entry; it never follows a final
            # symlink. The descriptor pins the `outputs` directory itself.
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


def _publish_into_private_outputs(rendered: Path, final_path: Path) -> None:
    """Atomically place a generated JPEG into a checked output directory.

    Linux uses a descriptor-pinned destination so a malicious `outputs`
    directory rename/symlink race cannot redirect a write outside the private
    root.  Platforms without dir-fd support still perform an immediate
    non-symlink directory check and never accept a caller-supplied pathname.
    """

    if not rendered.is_file() or rendered.is_symlink():
        raise VideoOperationError("Poster đầu ra không còn sẵn sàng", code="VIDEO_OUTPUT_INVALID")
    descriptors = _open_private_outputs_directory(final_path) if _private_directory_fd_supported() else None
    if _private_directory_fd_supported() and descriptors is None:
        raise VideoOperationError("Không thể khóa storage poster riêng tư", code="VIDEO_OUTPUT_INVALID")
    if descriptors is not None:
        _root_descriptor, outputs_descriptor = descriptors
        try:
            try:
                os.stat(final_path.name, dir_fd=outputs_descriptor, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise VideoOperationError("Không thể chuẩn bị poster riêng tư", code="VIDEO_OUTPUT_INVALID")
            os.replace(rendered, final_path.name, dst_dir_fd=outputs_descriptor)
            return
        except OSError as exc:
            raise VideoOperationError("Không thể chuẩn bị poster riêng tư", code="VIDEO_OUTPUT_INVALID") from exc
        finally:
            _close_private_outputs_directory(descriptors)
    parent_metadata = os.lstat(final_path.parent)
    if not stat.S_ISDIR(parent_metadata.st_mode) or stat.S_ISLNK(parent_metadata.st_mode):
        raise VideoOperationError("Không thể khóa storage poster riêng tư", code="VIDEO_OUTPUT_INVALID")
    if final_path.exists() or final_path.is_symlink():
        raise VideoOperationError("Không thể chuẩn bị poster riêng tư", code="VIDEO_OUTPUT_INVALID")
    try:
        os.replace(rendered, final_path)
    except OSError as exc:
        raise VideoOperationError("Không thể chuẩn bị poster riêng tư", code="VIDEO_OUTPUT_INVALID") from exc


def _open_verified_output(path: Path, *, expected_bytes: int, expected_digest: str, expected_width: int, expected_height: int) -> BinaryIO | None:
    if (
        expected_bytes < 1
        or expected_bytes > _maximum_output_bytes()
        or not SHA256_PATTERN.fullmatch(expected_digest.lower())
        or expected_width < 1
        or expected_height < 1
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
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, flags)
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
        if not hmac.compare_digest(_digest_open_stream(stream), expected_digest):
            return None
        width, height = _verify_jpeg_stream(stream)
        if (width, height) != (expected_width, expected_height):
            return None
        # Pillow may leave the verified descriptor at EOF. Reset the very
        # same pinned stream before handing it to StreamingResponse so a valid
        # JPEG can never be marked completed yet download as an empty body.
        stream.seek(0)
        accepted = stream
        stream = None
        return accepted
    except (OSError, VideoOperationError):
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
    expected_width: int,
    expected_height: int,
) -> BinaryIO | None:
    """Return an anonymous, rehashed JPEG snapshot for a safe download.

    The persisted output descriptor is revalidated before this function is
    called, but another local writer could still hold an inode handle.  Never
    stream that mutable persistent descriptor after verification.  This copies
    and validates its exact bytes into an anonymous temporary file, which is
    the only descriptor passed to ``StreamingResponse`` and is removed by its
    normal response finalizer.
    """

    sealed: BinaryIO | None = None
    try:
        if (
            expected_bytes < 1
            or expected_bytes > _maximum_output_bytes()
            or not SHA256_PATTERN.fullmatch(expected_digest.lower())
            or expected_width < 1
            or expected_height < 1
        ):
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
        # Parse the same temporary snapshot that will be handed to the
        # browser. A completed artifact can therefore never download a
        # different or malformed JPEG because a persistent file changed.
        sealed.seek(0)
        width, height = _verify_jpeg_stream(sealed)
        if (width, height) != (expected_width, expected_height):
            return None
        sealed.seek(0)
        accepted = sealed
        sealed = None
        return accepted
    except (OSError, ValueError, VideoOperationError):
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


def _stream_file(stream: BinaryIO, *, finalize: Callable[[], None]) -> Iterator[bytes]:
    try:
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            yield chunk
    finally:
        finalize()


def _attachment_response(stream: BinaryIO, *, byte_size: int) -> StreamingResponse:
    lock = threading.Lock()
    finalized = False

    def finalize() -> None:
        nonlocal finalized
        with lock:
            if finalized:
                return
            finalized = True
        stream.close()

    return StreamingResponse(
        _stream_file(stream, finalize=finalize),
        media_type="image/jpeg",
        background=BackgroundTask(finalize),
        headers={
            "Content-Length": str(byte_size),
            "Content-Disposition": "attachment; filename*=utf-8''toan-aas-video-poster.jpg",
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.get("")
async def list_video_operations(
    limit: int = Query(default=20, ge=1, le=100),
    account: dict = Depends(require_account),
):
    """List only the signed owner's private poster operation metadata."""

    _require_enabled()
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"SELECT {OPERATION_SELECT} FROM web_video_operations WHERE account_id=? ORDER BY updated_at DESC, id DESC LIMIT ?",
            (str(account["id"]), int(limit)),
        ).fetchall()
    return envelope(
        True,
        "Đã tải lịch sử Video Poster private.",
        data={"operations": [_operation_public(tuple(row)) for row in rows], "source": "web_native"},
        status_name="read_only",
    )


@router.get("/{operation_id}")
async def get_video_operation(operation_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã Video Poster")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = _operation_row(conn, operation_id, str(account["id"]))
        events = conn.execute(
            """SELECT state, created_at FROM web_video_operation_events
                 WHERE operation_id=? ORDER BY sequence ASC, id ASC LIMIT 20""",
            (operation_id,),
        ).fetchall()
    if not row:
        return envelope(False, "Không tìm thấy Video Poster.", status_name="guarded", error_code="VIDEO_OPERATION_NOT_FOUND")
    return envelope(
        True,
        "Đã tải trạng thái Video Poster.",
        data={
            "operation": _operation_public(tuple(row)),
            "events": [{"state": str(event[0]), "created_at": str(event[1])} for event in events],
        },
        status_name=str(row[3]) if str(row[3]) in OPERATION_STATES else "guarded",
    )


@router.post("/poster")
async def create_video_poster(
    payload: VideoPosterRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Create a verified Web-owned JPEG poster through one bounded runtime."""

    ffmpeg, ffprobe = _require_poster_enabled()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with transaction() as conn:
        source = _owner_video_source(conn, account_id=account_id, source_asset_id=payload.source_asset_id)
        if source is None:
            raise HTTPException(status_code=422, detail="Chỉ nhận video Asset Vault đang hoạt động, đúng định dạng và giới hạn Poster Lab")
        source_asset_id, extension, content_type, source_bytes, source_digest, _storage_key = source
        fingerprint = _request_fingerprint(
            source_asset_id=source_asset_id,
            source_sha256=source_digest,
            source_bytes=source_bytes,
            position=payload.poster_position,
        )
        existing = conn.execute(
            f"SELECT {OPERATION_SELECT}, request_fingerprint FROM web_video_operations WHERE account_id=? AND kind=? AND idempotency_key=?",
            (account_id, VIDEO_POSTER_KIND, payload.idempotency_key),
        ).fetchone()
        if existing:
            if not hmac.compare_digest(str(existing[-1]), fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã dùng cho Video Poster khác")
            return _operation_envelope(_operation_public(tuple(existing[:-1])), replay=True)
        operation_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_video_operations
                   (id, account_id, source_asset_id, kind, state, idempotency_key, request_fingerprint,
                    source_sha256, source_byte_size, source_extension, source_content_type, poster_position,
                    created_at, queued_at, updated_at)
                 VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                operation_id, account_id, source_asset_id, VIDEO_POSTER_KIND, payload.idempotency_key,
                fingerprint, source_digest, source_bytes, extension, content_type, payload.poster_position,
                now, now, now,
            ),
        )
        _record_event(conn, operation_id=operation_id, state="queued", when=now)
    operation = await run_in_threadpool(
        _execute_poster,
        operation_id,
        account_id,
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
        request_id=_request_id(request),
    )
    return _operation_envelope(operation)


async def download_video_operation(operation_id: str, account: dict = Depends(require_account)):
    """Stream only an owner-checked, reverified private JPEG poster."""

    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã Video Poster")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            """SELECT state, storage_key, content_type, byte_size, sha256, output_width, output_height
                 FROM web_video_operations WHERE id=? AND account_id=?""",
            (operation_id, str(account["id"])),
        ).fetchone()
    if not row or str(row[0]) != "completed":
        return envelope(False, "Poster video chưa sẵn sàng để tải.", status_name="guarded", error_code="VIDEO_OUTPUT_UNAVAILABLE")
    try:
        storage_key, content_type, byte_size, digest, width, height = str(row[1] or ""), str(row[2] or ""), int(row[3] or 0), str(row[4] or ""), int(row[5] or 0), int(row[6] or 0)
        if content_type != "image/jpeg":
            raise RuntimeError("MIME Video Poster không hợp lệ")
        path = _output_path(video_operations_directory(), storage_key)
        stream = _open_verified_output(path, expected_bytes=byte_size, expected_digest=digest, expected_width=width, expected_height=height)
    except (OSError, RuntimeError, ValueError):
        stream = None
    if stream is None:
        _mark_output_unavailable(operation_id, str(account["id"]))
        return envelope(False, "Poster video không còn integrity để tải.", status_name="unavailable", error_code="VIDEO_OUTPUT_UNAVAILABLE")
    sealed_stream = _seal_verified_output_for_delivery(
        stream,
        expected_bytes=byte_size,
        expected_digest=digest,
        expected_width=width,
        expected_height=height,
    )
    if sealed_stream is None:
        # The persisted artifact was verified above. A transient failure while
        # allocating or validating the anonymous delivery snapshot must not
        # incorrectly rewrite a completed operation as unavailable.
        return envelope(
            False,
            "Không thể chuẩn bị poster riêng tư để tải an toàn. Vui lòng thử lại.",
            status_name="guarded",
            error_code="VIDEO_DELIVERY_UNAVAILABLE",
        )
    try:
        return _attachment_response(sealed_stream, byte_size=byte_size)
    except Exception:
        sealed_stream.close()
        raise


@router.get("/{operation_id}/download")
async def download_video_operation_route(operation_id: str, account: dict = Depends(require_account)):
    return await download_video_operation(operation_id, account)


def reconcile_video_operation_storage(*, interrupted_before: str | None = None) -> None:
    """Fail closed for interrupted work and incomplete/orphan private blobs."""

    if not video_operations_enabled():
        return
    ensure_copyfast_schema()
    root = video_operations_directory()
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
            raise RuntimeError("Startup Video Operation reconciliation fence không hợp lệ") from exc
    now = utc_now()
    with transaction() as conn:
        query = "SELECT id, account_id FROM web_video_operations WHERE state IN ('queued', 'processing')"
        parameters: tuple[Any, ...] = ()
        if cutoff_fence:
            query += " AND COALESCE(started_at, queued_at, created_at, updated_at) < ?"
            parameters = (cutoff_fence,)
        interrupted = conn.execute(query, parameters).fetchall()
        for operation_id, account_id in interrupted:
            conn.execute(
                """UPDATE web_video_operations
                       SET state='failed', failure_code='VIDEO_OPERATION_INTERRUPTED', updated_at=?, revision=revision + 1
                     WHERE id=? AND account_id=? AND state IN ('queued', 'processing')""",
                (now, str(operation_id), str(account_id)),
            )
            conn.execute(
                """UPDATE web_video_operation_attempts
                       SET state='failed', completed_at=?, failure_code='VIDEO_OPERATION_INTERRUPTED'
                     WHERE operation_id=? AND account_id=? AND state IN ('claimed', 'running')""",
                (now, str(operation_id), str(account_id)),
            )
            _record_event(conn, operation_id=str(operation_id), state="failed", when=now)
        completed = conn.execute(
            """SELECT id, account_id, storage_key, byte_size, sha256, output_width, output_height
                 FROM web_video_operations WHERE state='completed'"""
        ).fetchall()
    known_storage: set[str] = set()
    for row in completed:
        operation_id, account_id, storage_key, byte_size, digest, width, height = row
        valid = False
        try:
            path = _output_path(root, str(storage_key or ""))
            stream = _open_verified_output(
                path,
                expected_bytes=int(byte_size or 0),
                expected_digest=str(digest or ""),
                expected_width=int(width or 0),
                expected_height=int(height or 0),
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
                    candidate.unlink()
            except OSError:
                continue
