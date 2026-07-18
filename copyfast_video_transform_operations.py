"""Bounded, private Video Finishing Lab for the standalone Web App.

The module upgrades the useful local Video Editor idea from the frozen
Telegram Bot into a Web-native, owner-scoped operation.  It accepts exactly
one private MP4 already held by Asset Vault and a deliberately small closed
specification (ratio, fit, colour preset, sharpen and audio preservation).
It does not accept paths, URLs, raw FFmpeg filters, text overlays, provider
handles, Bot jobs, wallet/Xu, PayOS or publishing instructions.

Each request copies a descriptor-pinned source to an isolated staging area,
validates it with fixed ``ffprobe`` argv, runs fixed list-argv ``ffmpeg``,
verifies the final H.264/AAC receipt and seals a rehashed anonymous snapshot
for download.  A database row becomes ``completed`` only after that final
verification succeeds.
"""

from __future__ import annotations

import asyncio
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
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr, field_validator
from starlette.concurrency import run_in_threadpool

from copyfast_assets import open_verified_private_asset_stream
from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import (
    asset_vault_enabled,
    ensure_copyfast_schema,
    transaction,
    utc_now,
    video_transform_operations_directory,
    video_transform_operations_enabled,
)
from copyfast_media_runtime import media_ffmpeg_capacity


router = APIRouter(prefix="/api/v1/video-transform-operations", tags=["Video Finishing Lab"])

VIDEO_TRANSFORM_KIND = "video_transform"
STATE_VALUES = frozenset({"queued", "processing", "completed", "failed", "guarded", "unavailable"})
ASPECT_RATIOS = {
    "9:16": (720, 1280),
    "16:9": (1280, 720),
    "1:1": (1080, 1080),
    "4:5": (864, 1080),
}
FIT_MODES = frozenset({"crop", "blur_pad"})
PRESETS = frozenset({"none", "clear", "tiktok_pop", "cinematic", "soft_clean"})
SOURCE_EXTENSION = ".mp4"
SOURCE_CONTENT_TYPE = "video/mp4"
SUPPORTED_AUDIO_CODECS = frozenset({"aac", "mp3", "opus", "vorbis", "flac", "pcm_s16le", "pcm_s24le"})

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
ASSET_STORAGE_KEY_PATTERN = re.compile(r"^objects/[0-9a-f]{32}\.blob$")
OUTPUT_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.mp4$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

CHUNK_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 25 * 1024 * 1024
MIN_DURATION_SECONDS = 0.2
MAX_DURATION_SECONDS = 60.0
MAX_SOURCE_DIMENSION = 4_096
MAX_SOURCE_PIXELS = 16 * 1024 * 1024
MAX_SOURCE_ASPECT = 12.0
MAX_OUTPUT_PIXELS = 1_600_000
PROBE_TIMEOUT_SECONDS = 8.0
RENDER_TIMEOUT_SECONDS = 75.0
# The renderer uses a fixed ``-t`` from the source receipt.  This small
# container/frame tolerance permits normal MP4 rounding but rejects a file
# materially shortened by a size cap or interrupted render.
OUTPUT_DURATION_TOLERANCE_SECONDS = 0.5
ORPHAN_RETENTION_SECONDS = 60 * 60
VIDEO_TRANSFORM_TOPOLOGY_SQLITE_SINGLE_REPLICA = "sqlite_single_replica"
REPLICA_COUNT_ENV_NAMES = ("RAILWAY_REPLICA_COUNT", "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT")
_DOWNLOAD_CAPACITY = threading.BoundedSemaphore(value=2)

OPERATION_SELECT = """id, account_id, source_asset_id, kind, state, idempotency_key,
                      request_fingerprint, source_sha256, source_byte_size, source_extension,
                      source_content_type, target_ratio, fit_mode, preset, sharpen,
                      preserve_audio, source_duration_ms, source_width, source_height,
                      output_duration_ms, output_width, output_height, output_has_audio,
                      storage_key, original_filename, content_type, byte_size, sha256,
                      failure_code, created_at, queued_at, started_at, completed_at,
                      updated_at, revision"""


class VideoTransformError(Exception):
    """A bounded failure whose public text never exposes media internals."""

    def __init__(self, message: str, *, code: str = "VIDEO_TRANSFORM_INVALID"):
        super().__init__(message)
        self.public_message = message
        self.code = code


class _SealedVideoTransformDeliveryError(RuntimeError):
    """A transient failure preparing an anonymous private download snapshot."""


class _SealedVideoTransformPreparation:
    """Cancellation-safe handoff for a stream prepared in the thread pool."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cancelled = False
        self._stream: BinaryIO | None = None

    def accept(self, stream: BinaryIO | None) -> BinaryIO | None:
        close_stream: BinaryIO | None = None
        with self._lock:
            if self._cancelled:
                close_stream = stream
            else:
                self._stream = stream
                return stream
        if close_stream is not None:
            try:
                close_stream.close()
            except (OSError, ValueError):
                pass
        return None

    def detach(self) -> BinaryIO | None:
        with self._lock:
            stream = self._stream
            self._stream = None
            return stream

    def cancel(self) -> None:
        stream: BinaryIO | None = None
        with self._lock:
            self._cancelled = True
            stream = self._stream
            self._stream = None
        if stream is not None:
            try:
                stream.close()
            except (OSError, ValueError):
                pass


class _SealedVideoTransformStreamingResponse(StreamingResponse):
    """Release the sealed stream and capacity even when a client disconnects."""

    def __init__(self, content: Iterator[bytes], *, on_close: Callable[[], None], **kwargs: Any) -> None:
        self._sealed_video_transform_on_close = on_close
        super().__init__(content, **kwargs)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._sealed_video_transform_on_close()


class _VideoTransformSpec(BaseModel):
    """The only browser-controllable transform values, all allowlisted."""

    model_config = ConfigDict(extra="forbid")

    source_asset_id: StrictStr = Field(min_length=36, max_length=36)
    target_ratio: StrictStr = Field(default="9:16", min_length=3, max_length=4)
    fit_mode: StrictStr = Field(default="crop", min_length=4, max_length=8)
    preset: StrictStr = Field(default="none", min_length=4, max_length=12)
    sharpen: StrictBool = False
    preserve_audio: StrictBool = True

    @field_validator("source_asset_id")
    @classmethod
    def validate_source_asset_id(cls, value: StrictStr) -> str:
        return _uuid(str(value), label="Asset Vault ID")

    @field_validator("target_ratio")
    @classmethod
    def validate_target_ratio(cls, value: StrictStr) -> str:
        candidate = str(value or "").strip()
        if candidate not in ASPECT_RATIOS:
            raise ValueError("Tỷ lệ chỉ nhận 9:16, 16:9, 1:1 hoặc 4:5")
        return candidate

    @field_validator("fit_mode")
    @classmethod
    def validate_fit_mode(cls, value: StrictStr) -> str:
        candidate = str(value or "").strip().lower()
        if candidate not in FIT_MODES:
            raise ValueError("Chế độ khung chỉ nhận crop hoặc blur_pad")
        return candidate

    @field_validator("preset")
    @classmethod
    def validate_preset(cls, value: StrictStr) -> str:
        candidate = str(value or "").strip().lower()
        if candidate not in PRESETS:
            raise ValueError("Preset chỉ nhận none, clear, tiktok_pop, cinematic hoặc soft_clean")
        return candidate


class VideoTransformEstimateRequest(_VideoTransformSpec):
    """A non-mutating plan for an owner-scoped source video."""


class VideoTransformRequest(_VideoTransformSpec):
    """One immutable source snapshot becomes one sealed MP4 output."""

    idempotency_key: StrictStr = Field(min_length=12, max_length=160)

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: StrictStr) -> str:
        return _idempotency_key(str(value))


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


def _feature_enabled() -> bool:
    return video_transform_operations_enabled() and asset_vault_enabled()


def _require_enabled() -> None:
    if not _feature_enabled():
        raise HTTPException(
            status_code=503,
            detail="Video Finishing Lab cần Asset Vault private và WEBAPP_VIDEO_TRANSFORM_OPERATIONS_ENABLED=true",
        )


def _topology_guarded_code() -> str | None:
    """Block this in-request SQLite executor without a single-replica proof."""

    topology = os.environ.get("WEBAPP_VIDEO_TRANSFORM_OPERATIONS_TOPOLOGY", "").strip().lower()
    if not topology:
        topology = os.environ.get("WEBAPP_VIDEO_OPERATIONS_TOPOLOGY", "").strip().lower()
    if topology != VIDEO_TRANSFORM_TOPOLOGY_SQLITE_SINGLE_REPLICA:
        return "VIDEO_TRANSFORM_TOPOLOGY_UNVERIFIED"
    attested = False
    for name in REPLICA_COUNT_ENV_NAMES:
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        attested = True
        try:
            replicas = int(raw)
        except ValueError:
            return "VIDEO_TRANSFORM_REPLICA_COUNT_UNVERIFIED"
        if replicas != 1:
            return "VIDEO_TRANSFORM_MULTI_REPLICA_BLOCKED"
    return None if attested else "VIDEO_TRANSFORM_REPLICA_COUNT_UNVERIFIED"


def _binary_path(primary_environment_name: str, fallback_environment_name: str, expected_name: str) -> str:
    """Resolve a trusted executable; no client-derived executable is possible."""

    configured = os.environ.get(primary_environment_name, "").strip() or os.environ.get(fallback_environment_name, "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise VideoTransformError("Runtime Video Finishing chưa có binary tuyệt đối đã kiểm định", code="VIDEO_TRANSFORM_RUNTIME_UNAVAILABLE")
    else:
        discovered = shutil.which(expected_name)
        if not discovered:
            raise VideoTransformError("Runtime Video Finishing chưa có FFmpeg/ffprobe", code="VIDEO_TRANSFORM_RUNTIME_UNAVAILABLE")
        candidate = Path(discovered)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise VideoTransformError("Runtime Video Finishing chưa có binary hợp lệ", code="VIDEO_TRANSFORM_RUNTIME_UNAVAILABLE") from exc
    accepted_names = {expected_name.lower(), f"{expected_name}.exe".lower()}
    if resolved.name.lower() not in accepted_names or not resolved.is_file():
        raise VideoTransformError("Runtime Video Finishing chưa có binary hợp lệ", code="VIDEO_TRANSFORM_RUNTIME_UNAVAILABLE")
    if os.name != "nt" and not os.access(resolved, os.X_OK):
        raise VideoTransformError("Runtime Video Finishing chưa có binary có thể chạy", code="VIDEO_TRANSFORM_RUNTIME_UNAVAILABLE")
    return str(resolved)


def _runtime() -> tuple[str, str]:
    return (
        _binary_path("WEBAPP_VIDEO_TRANSFORM_FFMPEG_BIN", "WEBAPP_VIDEO_FFMPEG_BIN", "ffmpeg"),
        _binary_path("WEBAPP_VIDEO_TRANSFORM_FFPROBE_BIN", "WEBAPP_VIDEO_FFPROBE_BIN", "ffprobe"),
    )


def ensure_video_transform_operations_runtime() -> None:
    """Fail closed during startup only after an operator explicitly enables it."""

    if not video_transform_operations_enabled():
        return
    if not asset_vault_enabled():
        raise RuntimeError("Video Finishing Lab cần WEBAPP_ASSET_VAULT_ENABLED=true")
    if _topology_guarded_code():
        raise RuntimeError("Video Finishing Lab cần topology SQLite single-replica đã được xác nhận")
    _runtime()


def _require_runtime() -> tuple[str, str]:
    _require_enabled()
    if _topology_guarded_code():
        raise HTTPException(
            status_code=503,
            detail="Video Finishing Lab chỉ chạy trên topology SQLite single-replica đã được xác nhận.",
        )
    try:
        return _runtime()
    except VideoTransformError as exc:
        raise HTTPException(status_code=503, detail=exc.public_message) from exc


def _maximum_output_bytes() -> int:
    raw = os.environ.get("WEBAPP_VIDEO_TRANSFORM_MAX_OUTPUT_MB", "25").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 25
    return max(1, min(megabytes, 100)) * 1024 * 1024


def _maximum_account_bytes() -> int:
    raw = os.environ.get("WEBAPP_VIDEO_TRANSFORM_QUOTA_MB", "250").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 250
    return max(1, min(megabytes, 5_000)) * 1024 * 1024


def _feature_root() -> Path:
    root = video_transform_operations_directory()
    if root.exists() and root.is_symlink():
        raise RuntimeError("Storage Video Finishing không được là symbolic link")
    return root.resolve()


def _private_directory(root: Path, name: str) -> Path:
    if name not in {".staging", "outputs"}:
        raise RuntimeError("Thư mục Video Finishing không hợp lệ")
    candidate = root.resolve() / name
    if candidate.exists() and candidate.is_symlink():
        raise RuntimeError("Thư mục Video Finishing không được là symbolic link")
    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise RuntimeError("Thư mục Video Finishing không hợp lệ")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError("Thư mục Video Finishing vượt ngoài storage riêng") from exc
    return resolved


def _staging_path(root: Path, suffix: str) -> Path:
    return _private_directory(root, ".staging") / f"{uuid.uuid4().hex}{suffix}"


def _output_path(root: Path, storage_key: str) -> Path:
    if not OUTPUT_STORAGE_KEY_PATTERN.fullmatch(str(storage_key or "")):
        raise RuntimeError("Storage key Video Finishing không hợp lệ")
    private_root = root.resolve()
    candidate = private_root / str(storage_key)
    try:
        candidate.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError("Storage key Video Finishing vượt ngoài storage riêng") from exc
    return candidate


def _safe_unlink(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.is_file() and not path.is_symlink():
            path.unlink()
    except OSError:
        pass


def _safe_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed and parsed not in {float("inf"), float("-inf")} else None


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _source_not_found() -> dict[str, Any]:
    return envelope(False, "Video nguồn không thuộc Asset Vault private đang hoạt động.", status_name="guarded", error_code="VIDEO_TRANSFORM_SOURCE_UNAVAILABLE")


def _operation_not_found() -> dict[str, Any]:
    return envelope(False, "Không tìm thấy Video Finishing riêng tư.", status_name="guarded", error_code="VIDEO_TRANSFORM_NOT_FOUND")


def _operation_unavailable() -> dict[str, Any]:
    return envelope(False, "Video Finishing không còn file đầu ra đã kiểm tra.", status_name="unavailable", error_code="VIDEO_TRANSFORM_OUTPUT_UNAVAILABLE")


def _source_for_account(conn: Any, *, source_asset_id: str, account_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """SELECT id, extension, content_type, byte_size, sha256, storage_key, state
           FROM web_asset_files WHERE id=? AND account_id=?""",
        (source_asset_id, account_id),
    ).fetchone()
    if row is None:
        return None
    try:
        source_id = str(row[0])
        extension = str(row[1] or "").lower()
        content_type = str(row[2] or "").lower()
        byte_size = int(row[3])
        digest = str(row[4] or "").lower()
        storage_key = str(row[5] or "")
        state = str(row[6] or "")
    except (IndexError, TypeError, ValueError):
        return None
    if (
        UUID_PATTERN.fullmatch(source_id) is None
        or extension != SOURCE_EXTENSION
        or content_type != SOURCE_CONTENT_TYPE
        or byte_size < 128
        or byte_size > MAX_SOURCE_BYTES
        or SHA256_PATTERN.fullmatch(digest) is None
        or ASSET_STORAGE_KEY_PATTERN.fullmatch(storage_key) is None
        or state != "active"
    ):
        return None
    return {
        "id": str(uuid.UUID(source_id)),
        "extension": extension,
        "content_type": content_type,
        "byte_size": byte_size,
        "sha256": digest,
        # The key is kept transiently for descriptor-pinned copying and is
        # never written to operation rows or serialized to the browser.
        "storage_key": storage_key,
    }


def _normalized_spec(payload: _VideoTransformSpec) -> dict[str, Any]:
    width, height = ASPECT_RATIOS[str(payload.target_ratio)]
    if width * height > MAX_OUTPUT_PIXELS:
        raise VideoTransformError("Tỷ lệ đầu ra vượt giới hạn Video Finishing", code="VIDEO_TRANSFORM_DIMENSION_LIMIT")
    return {
        "target_ratio": str(payload.target_ratio),
        "fit_mode": str(payload.fit_mode),
        "preset": str(payload.preset),
        "sharpen": bool(payload.sharpen),
        "preserve_audio": bool(payload.preserve_audio),
        "width": width,
        "height": height,
    }


def _request_fingerprint(*, source: dict[str, Any], spec: dict[str, Any]) -> str:
    """Bind idempotency to the immutable source snapshot and closed spec."""

    payload = {
        "source": {
            "id": str(source["id"]),
            "sha256": str(source["sha256"]),
            "byte_size": int(source["byte_size"]),
            "extension": str(source["extension"]),
            "content_type": str(source["content_type"]),
        },
        "spec": {
            "target_ratio": str(spec["target_ratio"]),
            "fit_mode": str(spec["fit_mode"]),
            "preset": str(spec["preset"]),
            "sharpen": bool(spec["sharpen"]),
            "preserve_audio": bool(spec["preserve_audio"]),
        },
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _record_event(conn: Any, *, operation_id: str, state: str, when: str | None = None) -> None:
    now = when or utc_now()
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 FROM web_video_transform_operation_events WHERE operation_id=?",
        (operation_id,),
    ).fetchone()
    sequence = int(row[0] or 1) if row else 1
    conn.execute(
        """INSERT INTO web_video_transform_operation_events (id, operation_id, state, sequence, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), operation_id, state, sequence, now),
    )


def _operation_for_account(conn: Any, operation_id: str, account_id: str) -> tuple[Any, ...] | None:
    row = conn.execute(
        f"SELECT {OPERATION_SELECT} FROM web_video_transform_operations WHERE id=? AND account_id=?",
        (operation_id, account_id),
    ).fetchone()
    return tuple(row) if row else None


def _replay_matches(operation: tuple[Any, ...], payload: VideoTransformRequest) -> bool:
    """Check a replay only against the stored snapshot, not current asset state."""

    try:
        if str(operation[3]) != VIDEO_TRANSFORM_KIND:
            return False
        if str(operation[2]) != str(payload.source_asset_id):
            return False
        stored_spec = {
            "target_ratio": str(operation[11]),
            "fit_mode": str(operation[12]),
            "preset": str(operation[13]),
            "sharpen": bool(int(operation[14])),
            "preserve_audio": bool(int(operation[15])),
        }
        source = {
            "id": str(operation[2]),
            "sha256": str(operation[7] or ""),
            "byte_size": int(operation[8]),
            "extension": str(operation[9] or ""),
            "content_type": str(operation[10] or ""),
        }
        fingerprint = _request_fingerprint(source=source, spec={**stored_spec, "width": 0, "height": 0})
    except (IndexError, TypeError, ValueError, KeyError):
        return False
    return (
        stored_spec["target_ratio"] == str(payload.target_ratio)
        and stored_spec["fit_mode"] == str(payload.fit_mode)
        and stored_spec["preset"] == str(payload.preset)
        and stored_spec["sharpen"] == bool(payload.sharpen)
        and stored_spec["preserve_audio"] == bool(payload.preserve_audio)
        and SHA256_PATTERN.fullmatch(fingerprint) is not None
        and hmac.compare_digest(str(operation[6] or ""), fingerprint)
    )


def _public_operation(operation: tuple[Any, ...]) -> dict[str, Any]:
    try:
        state = str(operation[4])
        output_bytes = int(operation[26]) if operation[26] is not None else None
        source_duration_ms = int(operation[16]) if operation[16] is not None else None
        source_width = int(operation[17]) if operation[17] is not None else None
        source_height = int(operation[18]) if operation[18] is not None else None
        output_duration_ms = int(operation[19]) if operation[19] is not None else None
        output_width = int(operation[20]) if operation[20] is not None else None
        output_height = int(operation[21]) if operation[21] is not None else None
        sharpen = bool(_safe_int(operation[14]) or 0)
        preserve_audio = bool(_safe_int(operation[15]) or 0)
        raw_output_has_audio = _safe_int(operation[22])
        output_has_audio = bool(raw_output_has_audio) if raw_output_has_audio is not None else None
    except (IndexError, TypeError, ValueError) as exc:
        raise VideoTransformError("Receipt Video Finishing không hợp lệ", code="VIDEO_TRANSFORM_RECEIPT_INVALID") from exc
    return {
        "id": str(operation[0]),
        "kind": VIDEO_TRANSFORM_KIND,
        "state": state if state in STATE_VALUES else "guarded",
        "target_ratio": str(operation[11]),
        "fit_mode": str(operation[12]),
        "preset": str(operation[13]),
        "sharpen": sharpen,
        "preserve_audio": preserve_audio,
        "source": {
            "duration_ms": source_duration_ms,
            "width": source_width,
            "height": source_height,
        },
        "output": {
            "available": state == "completed" and output_bytes is not None,
            "filename": str(operation[24]) if operation[24] else None,
            "content_type": str(operation[25]) if operation[25] else None,
            "byte_size": output_bytes,
            "duration_ms": output_duration_ms,
            "width": output_width,
            "height": output_height,
            "has_audio": output_has_audio,
        },
        "failure_code": str(operation[28]) if operation[28] else None,
        "created_at": str(operation[29]),
        "queued_at": str(operation[30]),
        "started_at": str(operation[31]) if operation[31] else None,
        "completed_at": str(operation[32]) if operation[32] else None,
        "updated_at": str(operation[33]),
    }


def _operation_response(operation: tuple[Any, ...], *, replay: bool = False) -> dict[str, Any]:
    public = _public_operation(operation)
    return envelope(
        True,
        "Đã dùng lại Video Finishing trước đó." if replay else "Video Finishing đã được tạo và kiểm tra riêng tư.",
        data={"operation": public, "replay": replay},
        status_name=str(public["state"]),
    )


def _error_status(code: str) -> int:
    if code.endswith("_TIMEOUT"):
        return 504
    if code in {"VIDEO_TRANSFORM_RUNTIME_UNAVAILABLE", "VIDEO_TRANSFORM_TOPOLOGY_UNVERIFIED"}:
        return 503
    if code.endswith("_LIMIT") or code.endswith("_TOO_LARGE"):
        return 413
    if code.endswith("_UNAVAILABLE"):
        return 409
    return 422


def _quota_available(conn: Any, *, account_id: str, additional_bytes: int) -> bool:
    row = conn.execute(
        """SELECT COALESCE(SUM(byte_size), 0) FROM web_video_transform_operations
           WHERE account_id=? AND state='completed'""",
        (account_id,),
    ).fetchone()
    used = int(row[0] or 0) if row else 0
    return used + max(0, int(additional_bytes)) <= _maximum_account_bytes()


def _mark_failed(operation_id: str, account_id: str, *, request: Request | None, code: str) -> None:
    if not operation_id:
        return
    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            "SELECT state FROM web_video_transform_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
        if not row or str(row[0]) not in {"queued", "processing"}:
            return
        conn.execute(
            """UPDATE web_video_transform_operations
               SET state='failed', failure_code=?, updated_at=?, revision=revision + 1
               WHERE id=? AND account_id=? AND state IN ('queued', 'processing')""",
            (code[:96], now, operation_id, account_id),
        )
        conn.execute(
            """UPDATE web_video_transform_operation_attempts
               SET state='failed', completed_at=?, failure_code=?
               WHERE operation_id=? AND account_id=? AND state='processing'""",
            (now, code[:96], operation_id, account_id),
        )
        _record_event(conn, operation_id=operation_id, state="failed", when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.video_transform.failed",
            request_id=_request_id(request) if request is not None else "startup",
            target=operation_id,
            detail=f"code={code[:80]}",
        )


def _mark_output_unavailable(operation_id: str, account_id: str) -> None:
    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            "SELECT state FROM web_video_transform_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
        if not row or str(row[0]) != "completed":
            return
        conn.execute(
            """UPDATE web_video_transform_operations
               SET state='unavailable', failure_code='VIDEO_TRANSFORM_OUTPUT_UNAVAILABLE', updated_at=?, revision=revision + 1
               WHERE id=? AND account_id=?""",
            (now, operation_id, account_id),
        )
        _record_event(conn, operation_id=operation_id, state="unavailable", when=now)


def _mark_source_unavailable(source_asset_id: str, account_id: str) -> None:
    if not source_asset_id:
        return
    with transaction() as conn:
        conn.execute(
            """UPDATE web_asset_files
               SET state='unavailable', updated_at=?, lifecycle_revision=lifecycle_revision + 1
               WHERE id=? AND account_id=? AND state='active'""",
            (utc_now(), source_asset_id, account_id),
        )


def _video_magic_matches(prefix: bytes) -> bool:
    return len(prefix) >= 12 and prefix[4:8] == b"ftyp"


def _copy_verified_source(destination: Path, *, source: dict[str, Any]) -> None:
    """Copy/hash an owner-scoped descriptor before FFmpeg opens media bytes."""

    stream = open_verified_private_asset_stream(
        storage_key=str(source["storage_key"]),
        expected_bytes=int(source["byte_size"]),
        expected_digest=str(source["sha256"]),
    )
    if stream is None:
        raise VideoTransformError("Video nguồn không còn vượt qua kiểm tra integrity", code="VIDEO_TRANSFORM_SOURCE_UNAVAILABLE")
    total = 0
    digest = hashlib.sha256()
    prefix = bytearray()
    try:
        try:
            with stream, destination.open("xb") as output:
                while True:
                    chunk = stream.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_SOURCE_BYTES:
                        raise VideoTransformError("Video nguồn vượt giới hạn 25 MB", code="VIDEO_TRANSFORM_SOURCE_TOO_LARGE")
                    if len(prefix) < 32:
                        prefix.extend(chunk[: 32 - len(prefix)])
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        except VideoTransformError:
            raise
        except OSError as exc:
            raise VideoTransformError("Không thể chuẩn bị video nguồn riêng tư", code="VIDEO_TRANSFORM_STAGING_UNAVAILABLE") from exc
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            pass
    if (
        total != int(source["byte_size"])
        or not hmac.compare_digest(digest.hexdigest(), str(source["sha256"]))
        or not _video_magic_matches(bytes(prefix))
    ):
        _safe_unlink(destination)
        raise VideoTransformError("Video nguồn không còn vượt qua kiểm tra integrity", code="VIDEO_TRANSFORM_SOURCE_UNAVAILABLE")


def _parse_frame_rate(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text or "/" not in text:
        return None
    left, right = text.split("/", 1)
    numerator = _safe_float(left)
    denominator = _safe_float(right)
    if numerator is None or denominator is None or denominator <= 0:
        return None
    result = numerator / denominator
    return result if result == result and result not in {float("inf"), float("-inf")} else None


def _probe_source(ffprobe: str, source: Path) -> dict[str, Any]:
    """Validate exactly one bounded primary video and at most one safe audio."""

    command = [
        ffprobe,
        "-v", "error",
        "-protocol_whitelist", "file,pipe",
        "-show_entries", "format=format_name,duration:stream=codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,channels,sample_rate,disposition",
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
        raise VideoTransformError("Kiểm tra video vượt thời gian an toàn", code="VIDEO_TRANSFORM_PROBE_TIMEOUT") from exc
    except OSError as exc:
        raise VideoTransformError("Không thể khởi động runtime Video Finishing", code="VIDEO_TRANSFORM_RUNTIME_UNAVAILABLE") from exc
    if completed.returncode != 0 or len(completed.stdout) > 16 * 1024:
        raise VideoTransformError("Video không vượt qua kiểm tra định dạng", code="VIDEO_TRANSFORM_PROBE_INVALID")
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VideoTransformError("Video không vượt qua kiểm tra định dạng", code="VIDEO_TRANSFORM_PROBE_INVALID") from exc
    streams = payload.get("streams") if isinstance(payload, dict) else None
    fmt = payload.get("format") if isinstance(payload, dict) else None
    if not isinstance(streams, list) or not isinstance(fmt, dict):
        raise VideoTransformError("Video không có stream hợp lệ", code="VIDEO_TRANSFORM_PROBE_INVALID")
    if "mp4" not in str(fmt.get("format_name") or "").lower().split(","):
        raise VideoTransformError("Video nguồn không phải MP4 hợp lệ", code="VIDEO_TRANSFORM_PROBE_INVALID")
    videos = [stream for stream in streams if isinstance(stream, dict) and str(stream.get("codec_type") or "") == "video"]
    audios = [stream for stream in streams if isinstance(stream, dict) and str(stream.get("codec_type") or "") == "audio"]
    if len(videos) != 1 or len(audios) > 1 or any(str(stream.get("codec_type") or "") not in {"video", "audio"} for stream in streams if isinstance(stream, dict)):
        raise VideoTransformError("Video nguồn có cấu trúc stream chưa được hỗ trợ", code="VIDEO_TRANSFORM_PROBE_INVALID")
    video = videos[0]
    disposition = video.get("disposition") if isinstance(video.get("disposition"), dict) else {}
    duration = _safe_float(fmt.get("duration"))
    width = _safe_int(video.get("width"))
    height = _safe_int(video.get("height"))
    frame_rate = _parse_frame_rate(video.get("avg_frame_rate")) or _parse_frame_rate(video.get("r_frame_rate"))
    codec = str(video.get("codec_name") or "").lower()
    if (
        bool(disposition.get("attached_pic"))
        or codec not in {"h264", "hevc", "vp8", "vp9"}
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
        or frame_rate is None
        or frame_rate < 1.0
        or frame_rate > 60.0
    ):
        raise VideoTransformError("Video nguồn vượt giới hạn Video Finishing an toàn", code="VIDEO_TRANSFORM_PROBE_LIMIT")
    audio_codec = ""
    if audios:
        audio = audios[0]
        audio_codec = str(audio.get("codec_name") or "").lower()
        channels = _safe_int(audio.get("channels"))
        sample_rate = _safe_int(audio.get("sample_rate"))
        if channels is None or channels < 1 or channels > 2 or sample_rate is None or sample_rate < 8_000 or sample_rate > 96_000:
            raise VideoTransformError("Audio nguồn vượt giới hạn Video Finishing an toàn", code="VIDEO_TRANSFORM_AUDIO_LIMIT")
    return {
        "duration_seconds": duration,
        "duration_ms": int(round(duration * 1000)),
        "width": width,
        "height": height,
        "has_audio": bool(audios),
        "audio_codec": audio_codec,
    }


def _preset_filter(preset: str, *, sharpen: bool) -> str:
    """Return only constant server-owned visual filters for one allowed preset."""

    filters = {
        "none": "",
        "clear": "eq=brightness=0.010:contrast=1.060:saturation=1.060",
        "tiktok_pop": "eq=brightness=0.015:contrast=1.100:saturation=1.180",
        "cinematic": "eq=brightness=-0.010:contrast=1.130:saturation=0.940:gamma=0.970",
        "soft_clean": "eq=brightness=0.020:contrast=0.990:saturation=0.960",
    }
    selected = filters.get(preset)
    if selected is None:
        raise VideoTransformError("Preset Video Finishing không hợp lệ", code="VIDEO_TRANSFORM_INVALID")
    result = selected
    if sharpen:
        result = ",".join(item for item in (result, "unsharp=5:5:0.60:5:5:0.0") if item)
    return result


def _filter_graph(*, width: int, height: int, fit_mode: str, preset: str, sharpen: bool) -> str:
    """Create a filter graph exclusively from closed server constants.

    No raw graph, source path, crop coordinate, text, URL or setting from the
    browser enters this string.  ``blur_pad`` actually composes a blurred
    cover background rather than labelling an ordinary coloured pad as blur.
    """

    if width < 2 or height < 2 or width % 2 or height % 2:
        raise VideoTransformError("Kích thước đầu ra Video Finishing không hợp lệ", code="VIDEO_TRANSFORM_DIMENSION_LIMIT")
    visual = _preset_filter(preset, sharpen=sharpen)
    visual_suffix = f",{visual}" if visual else ""
    if fit_mode == "crop":
        return (
            f"[0:v]fps=30,scale={width}:{height}:force_original_aspect_ratio=increase:force_divisible_by=2:flags=lanczos,"
            f"crop={width}:{height}:(in_w-out_w)/2:(in_h-out_h)/2,setsar=1{visual_suffix},format=yuv420p[vout]"
        )
    if fit_mode == "blur_pad":
        return (
            f"[0:v]split=2[bgsrc][fgsrc];"
            f"[bgsrc]fps=30,scale={width}:{height}:force_original_aspect_ratio=increase:force_divisible_by=2:flags=lanczos,"
            f"crop={width}:{height}:(in_w-out_w)/2:(in_h-out_h)/2,setsar=1,format=yuv420p,gblur=sigma=20:steps=2[bg];"
            f"[fgsrc]fps=30,scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos,"
            f"setsar=1,format=yuv420p[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2:shortest=1{visual_suffix},format=yuv420p[vout]"
        )
    raise VideoTransformError("Chế độ khung Video Finishing không hợp lệ", code="VIDEO_TRANSFORM_INVALID")


def _render_transform(
    ffmpeg: str,
    source: Path,
    destination: Path,
    *,
    spec: dict[str, Any],
    source_duration_seconds: float,
    source_has_audio: bool,
) -> None:
    """Run one non-shell, fixed-argument H.264/AAC transformation."""

    graph = _filter_graph(
        width=int(spec["width"]),
        height=int(spec["height"]),
        fit_mode=str(spec["fit_mode"]),
        preset=str(spec["preset"]),
        sharpen=bool(spec["sharpen"]),
    )
    command = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-v", "error",
        "-xerror",
        "-threads", "1",
        "-filter_threads", "1",
        "-filter_complex_threads", "1",
        "-protocol_whitelist", "file,pipe",
        "-i", str(source),
        "-filter_complex", graph,
        "-map", "[vout]",
    ]
    preserve_audio = bool(spec["preserve_audio"]) and source_has_audio
    if preserve_audio:
        command.extend(["-map", "0:a:0?", "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2"])
    else:
        command.append("-an")
    command.extend(
        [
            "-sn",
            "-dn",
            "-map_metadata", "-1",
            "-map_chapters", "-1",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-t", f"{float(source_duration_seconds):.3f}",
            "-movflags", "+faststart",
            # Bound disk growth while FFmpeg writes.  The value is derived
            # only from the server-side deployment cap; post-render probing
            # below remains the second enforcement layer.
            "-fs", str(_maximum_output_bytes()),
            "-f", "mp4",
            "-n",
            str(destination),
        ]
    )
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
        raise VideoTransformError("Hoàn thiện video vượt thời gian an toàn", code="VIDEO_TRANSFORM_RENDER_TIMEOUT") from exc
    except OSError as exc:
        raise VideoTransformError("Không thể khởi động runtime Video Finishing", code="VIDEO_TRANSFORM_RUNTIME_UNAVAILABLE") from exc
    if completed.returncode != 0:
        raise VideoTransformError("Không thể hoàn thiện video này an toàn", code="VIDEO_TRANSFORM_RENDER_FAILED")


def _digest_stream(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    stream.seek(0)
    while True:
        chunk = stream.read(CHUNK_BYTES)
        if not chunk:
            break
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest()


def _probe_output(
    ffprobe: str,
    path: Path,
    *,
    expected_width: int,
    expected_height: int,
    expected_duration_seconds: float,
    expected_audio: bool,
) -> tuple[int, bool]:
    """Verify the exact H.264 + optional AAC output stream contract."""

    command = [
        ffprobe,
        "-v", "error",
        "-protocol_whitelist", "file,pipe",
        "-show_entries", "format=format_name,duration:stream=codec_type,codec_name,width,height,pix_fmt,avg_frame_rate,r_frame_rate,channels,sample_rate,duration",
        "-of", "json",
        str(path),
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
        raise VideoTransformError("Kiểm tra video đầu ra vượt thời gian an toàn", code="VIDEO_TRANSFORM_PROBE_TIMEOUT") from exc
    except OSError as exc:
        raise VideoTransformError("Không thể khởi động kiểm tra Video Finishing", code="VIDEO_TRANSFORM_RUNTIME_UNAVAILABLE") from exc
    if completed.returncode != 0 or len(completed.stdout) > 16 * 1024:
        raise VideoTransformError("Video đầu ra không vượt qua kiểm tra định dạng", code="VIDEO_TRANSFORM_OUTPUT_INVALID")
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VideoTransformError("Video đầu ra không vượt qua kiểm tra định dạng", code="VIDEO_TRANSFORM_OUTPUT_INVALID") from exc
    streams = payload.get("streams") if isinstance(payload, dict) else None
    fmt = payload.get("format") if isinstance(payload, dict) else None
    if not isinstance(streams, list) or not isinstance(fmt, dict) or "mp4" not in str(fmt.get("format_name") or "").lower().split(","):
        raise VideoTransformError("Video đầu ra không có stream MP4 hợp lệ", code="VIDEO_TRANSFORM_OUTPUT_INVALID")
    videos = [stream for stream in streams if isinstance(stream, dict) and str(stream.get("codec_type") or "") == "video"]
    audios = [stream for stream in streams if isinstance(stream, dict) and str(stream.get("codec_type") or "") == "audio"]
    if len(videos) != 1 or len(audios) != (1 if expected_audio else 0) or any(str(stream.get("codec_type") or "") not in {"video", "audio"} for stream in streams if isinstance(stream, dict)):
        raise VideoTransformError("Video đầu ra có stream chưa được phép", code="VIDEO_TRANSFORM_OUTPUT_INVALID")
    video = videos[0]
    duration = _safe_float(fmt.get("duration")) or _safe_float(video.get("duration"))
    width = _safe_int(video.get("width"))
    height = _safe_int(video.get("height"))
    frame_rate = _parse_frame_rate(video.get("avg_frame_rate")) or _parse_frame_rate(video.get("r_frame_rate"))
    if (
        str(video.get("codec_name") or "").lower() != "h264"
        or str(video.get("pix_fmt") or "").lower() != "yuv420p"
        or width != expected_width
        or height != expected_height
        or duration is None
        or duration < MIN_DURATION_SECONDS
        or duration > MAX_DURATION_SECONDS
        or abs(duration - expected_duration_seconds) > OUTPUT_DURATION_TOLERANCE_SECONDS
        or frame_rate is None
        or abs(frame_rate - 30.0) > 0.05
    ):
        raise VideoTransformError("Video đầu ra không khớp thông số đã xác nhận", code="VIDEO_TRANSFORM_OUTPUT_INVALID")
    if audios:
        audio = audios[0]
        if (
            str(audio.get("codec_name") or "").lower() != "aac"
            or (_safe_int(audio.get("channels")) or 0) not in {1, 2}
            or (_safe_int(audio.get("sample_rate")) or 0) != 48_000
        ):
            raise VideoTransformError("Audio đầu ra không khớp thông số đã xác nhận", code="VIDEO_TRANSFORM_OUTPUT_INVALID")
    return int(round(duration * 1000)), bool(audios)


def _verify_mp4_output(
    path: Path,
    *,
    ffprobe: str,
    expected_width: int,
    expected_height: int,
    expected_duration_seconds: float,
    expected_audio: bool,
    expected_bytes: int | None = None,
    expected_digest: str | None = None,
) -> tuple[int, str, int, bool]:
    """Verify storage integrity, MP4 magic, digest and media stream receipt."""

    try:
        if not path.is_file() or path.is_symlink():
            raise VideoTransformError("Video đầu ra không còn integrity", code="VIDEO_TRANSFORM_OUTPUT_INVALID")
        byte_size = int(path.stat().st_size)
        if byte_size < 128:
            raise VideoTransformError("Video đầu ra không còn integrity", code="VIDEO_TRANSFORM_OUTPUT_INVALID")
        # On download, receipt integrity takes precedence over a mutable
        # deployment policy. A replacement file must never masquerade as a
        # legitimate historical artifact that merely exceeds a newer cap.
        if expected_bytes is not None and byte_size != int(expected_bytes):
            raise VideoTransformError("Video đầu ra không còn integrity", code="VIDEO_TRANSFORM_OUTPUT_INVALID")
        if byte_size > _maximum_output_bytes():
            raise VideoTransformError("Video đầu ra vượt giới hạn lưu trữ", code="VIDEO_TRANSFORM_OUTPUT_LIMIT")
        with path.open("rb") as stream:
            prefix = stream.read(16)
            stream.seek(0)
            digest = _digest_stream(stream)
        if not _video_magic_matches(prefix):
            raise VideoTransformError("Video đầu ra không phải MP4 hợp lệ", code="VIDEO_TRANSFORM_OUTPUT_INVALID")
        if expected_digest is not None and not hmac.compare_digest(digest, str(expected_digest)):
            raise VideoTransformError("Video đầu ra không còn integrity", code="VIDEO_TRANSFORM_OUTPUT_INVALID")
        duration_ms, has_audio = _probe_output(
            ffprobe,
            path,
            expected_width=expected_width,
            expected_height=expected_height,
            expected_duration_seconds=expected_duration_seconds,
            expected_audio=expected_audio,
        )
        return byte_size, digest, duration_ms, has_audio
    except VideoTransformError:
        raise
    except OSError as exc:
        raise VideoTransformError("Video đầu ra không còn integrity", code="VIDEO_TRANSFORM_OUTPUT_INVALID") from exc


def _publish_verified_output(root: Path, rendered: Path) -> tuple[Path, str]:
    """Atomically promote one verified staging MP4 to the private output root."""

    outputs = _private_directory(root, "outputs")
    storage_key = f"outputs/{uuid.uuid4().hex}.mp4"
    final_path = _output_path(root, storage_key)
    if final_path.parent != outputs or final_path.exists():
        raise VideoTransformError("Không thể xuất Video Finishing riêng tư", code="VIDEO_TRANSFORM_STAGING_UNAVAILABLE")
    try:
        os.replace(rendered, final_path)
    except OSError as exc:
        raise VideoTransformError("Không thể xuất Video Finishing riêng tư", code="VIDEO_TRANSFORM_STAGING_UNAVAILABLE") from exc
    return final_path, storage_key


def _open_verified_output(path: Path, *, expected_bytes: int, expected_digest: str) -> BinaryIO | None:
    """Pin and hash an output descriptor without following a final symlink."""

    flags = os.O_RDONLY | int(getattr(os, "O_NOFOLLOW", 0))
    stream: BinaryIO | None = None
    try:
        stream = os.fdopen(os.open(path, flags), "rb", closefd=True)
        metadata = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(metadata.st_mode)
            or int(metadata.st_size) != expected_bytes
            or expected_bytes < 128
            or expected_bytes > _maximum_output_bytes()
        ):
            return None
        prefix = stream.read(16)
        if not _video_magic_matches(prefix):
            return None
        stream.seek(0)
        if not hmac.compare_digest(_digest_stream(stream), expected_digest):
            return None
        accepted = stream
        stream = None
        return accepted
    except (OSError, ValueError):
        return None
    finally:
        if stream is not None:
            try:
                stream.close()
            except (OSError, ValueError):
                pass


def _seal_verified_output_for_delivery(stream: BinaryIO, *, expected_bytes: int, expected_digest: str) -> BinaryIO | None:
    """Copy/re-hash a descriptor-pinned output to an anonymous temporary file."""

    sealed: BinaryIO | None = None
    try:
        if expected_bytes < 128 or expected_bytes > _maximum_output_bytes() or SHA256_PATTERN.fullmatch(expected_digest) is None:
            return None
        sealed = tempfile.TemporaryFile(mode="w+b")
        digest = hashlib.sha256()
        byte_count = 0
        stream.seek(0)
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            byte_count += len(chunk)
            if byte_count > expected_bytes:
                return None
            digest.update(chunk)
            sealed.write(chunk)
        if byte_count != expected_bytes or not hmac.compare_digest(digest.hexdigest(), expected_digest):
            return None
        sealed.seek(0)
        accepted = sealed
        sealed = None
        return accepted
    except (OSError, ValueError) as exc:
        raise _SealedVideoTransformDeliveryError("Không thể chuẩn bị luồng tải Video Finishing private") from exc
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            pass
        if sealed is not None:
            try:
                sealed.close()
            except OSError:
                pass


def _prepare_sealed_output_for_handoff(
    handoff: _SealedVideoTransformPreparation,
    path: Path,
    *,
    expected_bytes: int,
    expected_digest: str,
) -> BinaryIO | None:
    """Seal a stream and hand it to an awaiter without cancellation leaks."""

    return handoff.accept(
        _prepare_sealed_output(path, expected_bytes=expected_bytes, expected_digest=expected_digest)
    )


def _reserve_download_capacity() -> None:
    if not _DOWNLOAD_CAPACITY.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Đang có nhiều lượt tải Video Finishing private; vui lòng thử lại sau ít phút")


def _release_download_capacity() -> None:
    try:
        _DOWNLOAD_CAPACITY.release()
    except ValueError:
        pass


def _sealed_download_finalizer(stream: BinaryIO) -> Callable[[], None]:
    lock = threading.Lock()
    finalized = False

    def finalize() -> None:
        nonlocal finalized
        with lock:
            if finalized:
                return
            finalized = True
        try:
            stream.close()
        except (OSError, ValueError):
            pass
        finally:
            _release_download_capacity()

    return finalize


def _output_chunks(stream: BinaryIO, *, finalize: Callable[[], None]) -> Iterator[bytes]:
    try:
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            yield chunk
    finally:
        finalize()


def _attachment_response(stream: BinaryIO, *, byte_size: int, filename: str, on_close: Callable[[], None]) -> StreamingResponse:
    if byte_size < 128:
        on_close()
        raise ValueError("Kích thước Video Finishing không hợp lệ")
    safe_name = str(filename or "toan-aas-video-finished.mp4").replace("\r", " ").replace("\n", " ").strip()
    if not safe_name:
        safe_name = "toan-aas-video-finished.mp4"
    return _SealedVideoTransformStreamingResponse(
        _output_chunks(stream, finalize=on_close),
        on_close=on_close,
        media_type="video/mp4",
        headers={
            "Content-Length": str(byte_size),
            "Content-Disposition": f"attachment; filename*=utf-8''{quote(safe_name)}",
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
        },
    )


def _prepare_sealed_output(path: Path, *, expected_bytes: int, expected_digest: str) -> BinaryIO | None:
    pinned = _open_verified_output(path, expected_bytes=expected_bytes, expected_digest=expected_digest)
    if pinned is None:
        return None
    return _seal_verified_output_for_delivery(pinned, expected_bytes=expected_bytes, expected_digest=expected_digest)


def _completed_output_details(operation: tuple[Any, ...]) -> tuple[Path, int, str, int, int, float, bool]:
    try:
        storage_key = str(operation[23] or "")
        byte_size = int(operation[26] or 0)
        digest = str(operation[27] or "")
        width = int(operation[20] or 0)
        height = int(operation[21] or 0)
        source_duration_ms = int(operation[16] or 0)
        has_audio = bool(int(operation[22] or 0))
    except (IndexError, TypeError, ValueError) as exc:
        raise VideoTransformError("Receipt Video Finishing không hợp lệ", code="VIDEO_TRANSFORM_OUTPUT_INVALID") from exc
    if (
        not storage_key
        or byte_size < 128
        or SHA256_PATTERN.fullmatch(digest) is None
        or width < 1
        or height < 1
        or source_duration_ms < 1
    ):
        raise VideoTransformError("Receipt Video Finishing không hợp lệ", code="VIDEO_TRANSFORM_OUTPUT_INVALID")
    return _output_path(_feature_root(), storage_key), byte_size, digest, width, height, source_duration_ms / 1000.0, has_audio


@router.post("/estimate")
async def estimate_video_transform(
    payload: VideoTransformEstimateRequest,
    account: dict = Depends(require_account),
):
    """Return a safe non-mutating plan; it creates no files or DB receipt."""

    _require_runtime()
    ensure_copyfast_schema()
    spec = _normalized_spec(payload)
    with transaction() as conn:
        source = _source_for_account(conn, source_asset_id=str(payload.source_asset_id), account_id=str(account["id"]))
    if source is None:
        return _source_not_found()
    return envelope(
        True,
        "Đã kiểm tra kế hoạch Video Finishing; chưa tạo file và chưa ghi dữ liệu.",
        data={
            "estimate": {
                "target_ratio": spec["target_ratio"],
                "fit_mode": spec["fit_mode"],
                "preset": spec["preset"],
                "sharpen": bool(spec["sharpen"]),
                "preserve_audio": bool(spec["preserve_audio"]),
                "output": {
                    "content_type": "video/mp4",
                    "video_codec": "h264",
                    "audio": "aac_if_source_has_supported_audio" if spec["preserve_audio"] else "none",
                    "width": spec["width"],
                    "height": spec["height"],
                },
            }
        },
        status_name="draft",
    )


@router.get("")
async def list_video_transform_operations(
    limit: int = 20,
    offset: int = Query(0, ge=0, le=10_000),
    account: dict = Depends(require_account),
):
    _require_enabled()
    ensure_copyfast_schema()
    bounded_limit = max(1, min(int(limit), 50))
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT {OPERATION_SELECT} FROM web_video_transform_operations
                WHERE account_id=? ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (str(account["id"]), bounded_limit + 1, int(offset)),
        ).fetchall()
    operations = [tuple(row) for row in rows[:bounded_limit]]
    public = [_public_operation(operation) for operation in operations]
    return envelope(
        True,
        "Đã tải Video Finishing riêng tư.",
        data={
            "items": public,
            "pagination": {
                "offset": int(offset),
                "returned": len(public),
                "has_more": len(rows) > bounded_limit,
                "next_offset": int(offset) + bounded_limit if len(rows) > bounded_limit else None,
            },
        },
        status_name="completed",
    )


@router.post("")
async def create_video_transform(
    payload: VideoTransformRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Create one sealed private H.264/AAC (or mute) transform receipt."""

    _require_enabled()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    spec = _normalized_spec(payload)
    operation_id = ""
    source: dict[str, Any] | None = None
    active_source_id = str(payload.source_asset_id)
    source_staging: Path | None = None
    rendered: Path | None = None
    final_path: Path | None = None
    capacity_reserved = False
    try:
        # An existing receipt is returned before source lookup/runtime work so
        # an archived source cannot turn a prior idempotent success into a new
        # operation or conceal the deterministic replay result.
        with transaction() as conn:
            existing = conn.execute(
                f"""SELECT {OPERATION_SELECT} FROM web_video_transform_operations
                    WHERE account_id=? AND kind=? AND idempotency_key=?""",
                (account_id, VIDEO_TRANSFORM_KIND, str(payload.idempotency_key)),
            ).fetchone()
            if existing:
                operation = tuple(existing)
                if _replay_matches(operation, payload):
                    return _operation_response(operation, replay=True)
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho Video Finishing khác")
            source = _source_for_account(conn, source_asset_id=str(payload.source_asset_id), account_id=account_id)
        if source is None:
            return _source_not_found()

        # A new request needs the attested runtime. An already-completed
        # immutable idempotency receipt above must remain readable during a
        # temporary runtime/topology maintenance window.
        ffmpeg, ffprobe = _require_runtime()
        root = _feature_root()
        if not media_ffmpeg_capacity().acquire(blocking=False):
            raise HTTPException(status_code=429, detail="Video Finishing đang bận render một tác vụ media khác; vui lòng thử lại sau ít phút")
        capacity_reserved = True
        source_staging = _staging_path(root, ".source.mp4")
        await run_in_threadpool(_copy_verified_source, source_staging, source=source)
        source_media = await run_in_threadpool(_probe_source, ffprobe, source_staging)
        if bool(spec["preserve_audio"]) and bool(source_media["has_audio"]) and str(source_media["audio_codec"]) not in SUPPORTED_AUDIO_CODECS:
            raise VideoTransformError("Audio nguồn chưa có codec an toàn để giữ lại", code="VIDEO_TRANSFORM_AUDIO_UNSUPPORTED")

        fingerprint = _request_fingerprint(source=source, spec=spec)
        with transaction() as conn:
            existing = conn.execute(
                f"""SELECT {OPERATION_SELECT} FROM web_video_transform_operations
                    WHERE account_id=? AND kind=? AND idempotency_key=?""",
                (account_id, VIDEO_TRANSFORM_KIND, str(payload.idempotency_key)),
            ).fetchone()
            if existing:
                operation = tuple(existing)
                if _replay_matches(operation, payload):
                    return _operation_response(operation, replay=True)
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho Video Finishing khác")
            current_source = _source_for_account(conn, source_asset_id=str(payload.source_asset_id), account_id=account_id)
            if current_source is None or current_source != source:
                return _source_not_found()
            now = utc_now()
            operation_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO web_video_transform_operations
                   (id, account_id, source_asset_id, kind, state, idempotency_key, request_fingerprint,
                    source_sha256, source_byte_size, source_extension, source_content_type,
                    target_ratio, fit_mode, preset, sharpen, preserve_audio,
                    source_duration_ms, source_width, source_height, created_at, queued_at, updated_at)
                   VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    operation_id,
                    account_id,
                    str(source["id"]),
                    VIDEO_TRANSFORM_KIND,
                    str(payload.idempotency_key),
                    fingerprint,
                    str(source["sha256"]),
                    int(source["byte_size"]),
                    str(source["extension"]),
                    str(source["content_type"]),
                    str(spec["target_ratio"]),
                    str(spec["fit_mode"]),
                    str(spec["preset"]),
                    1 if bool(spec["sharpen"]) else 0,
                    1 if bool(spec["preserve_audio"]) else 0,
                    int(source_media["duration_ms"]),
                    int(source_media["width"]),
                    int(source_media["height"]),
                    now,
                    now,
                    now,
                ),
            )
            _record_event(conn, operation_id=operation_id, state="queued", when=now)
            conn.execute(
                """UPDATE web_video_transform_operations
                   SET state='processing', started_at=?, updated_at=?, revision=revision + 1
                   WHERE id=? AND account_id=? AND state='queued'""",
                (now, now, operation_id, account_id),
            )
            conn.execute(
                """INSERT INTO web_video_transform_operation_attempts
                   (id, operation_id, account_id, attempt_no, state, fence_token, started_at)
                   VALUES (?, ?, ?, 1, 'processing', ?, ?)""",
                (str(uuid.uuid4()), operation_id, account_id, str(uuid.uuid4()), now),
            )
            _record_event(conn, operation_id=operation_id, state="processing", when=now)

        rendered = _staging_path(root, ".rendered.mp4")
        expected_audio = bool(spec["preserve_audio"]) and bool(source_media["has_audio"])
        await run_in_threadpool(
            _render_transform,
            ffmpeg,
            source_staging,
            rendered,
            spec=spec,
            source_duration_seconds=float(source_media["duration_seconds"]),
            source_has_audio=bool(source_media["has_audio"]),
        )
        output_bytes, output_digest, output_duration_ms, output_has_audio = await run_in_threadpool(
            _verify_mp4_output,
            rendered,
            ffprobe=ffprobe,
            expected_width=int(spec["width"]),
            expected_height=int(spec["height"]),
            expected_duration_seconds=float(source_media["duration_seconds"]),
            expected_audio=expected_audio,
        )
        final_path, storage_key = await run_in_threadpool(_publish_verified_output, root, rendered)
        output_bytes, output_digest, output_duration_ms, output_has_audio = await run_in_threadpool(
            _verify_mp4_output,
            final_path,
            ffprobe=ffprobe,
            expected_width=int(spec["width"]),
            expected_height=int(spec["height"]),
            expected_duration_seconds=float(source_media["duration_seconds"]),
            expected_audio=expected_audio,
            expected_bytes=output_bytes,
            expected_digest=output_digest,
        )
        now = utc_now()
        filename = f"toan-aas-video-finished-{operation_id}.mp4"
        with transaction() as conn:
            current = conn.execute(
                "SELECT state FROM web_video_transform_operations WHERE id=? AND account_id=?",
                (operation_id, account_id),
            ).fetchone()
            if not current or str(current[0]) != "processing":
                raise RuntimeError("Video Finishing không còn ở trạng thái có thể hoàn tất")
            if not _quota_available(conn, account_id=account_id, additional_bytes=output_bytes):
                raise HTTPException(status_code=413, detail="Video Finishing đã đạt quota lưu trữ của Web account")
            conn.execute(
                """UPDATE web_video_transform_operations
                   SET state='completed', output_duration_ms=?, output_width=?, output_height=?, output_has_audio=?,
                       storage_key=?, original_filename=?, content_type='video/mp4', byte_size=?, sha256=?,
                       completed_at=?, updated_at=?, failure_code=NULL, revision=revision + 1
                   WHERE id=? AND account_id=? AND state='processing'""",
                (
                    output_duration_ms,
                    int(spec["width"]),
                    int(spec["height"]),
                    1 if output_has_audio else 0,
                    storage_key,
                    filename,
                    output_bytes,
                    output_digest,
                    now,
                    now,
                    operation_id,
                    account_id,
                ),
            )
            conn.execute(
                """UPDATE web_video_transform_operation_attempts
                   SET state='completed', completed_at=?, failure_code=NULL
                   WHERE operation_id=? AND account_id=? AND state='processing'""",
                (now, operation_id, account_id),
            )
            _record_event(conn, operation_id=operation_id, state="completed", when=now)
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="web.video_transform.created",
                request_id=_request_id(request),
                target=operation_id,
                detail=(
                    f"ratio={spec['target_ratio']};fit={spec['fit_mode']};preset={spec['preset']};"
                    f"sharpen={int(bool(spec['sharpen']))};audio={int(output_has_audio)};"
                    f"duration_ms={output_duration_ms};bytes={output_bytes}"
                ),
            )
            completed = _operation_for_account(conn, operation_id, account_id)
        if completed is None:
            raise RuntimeError("Không thể đọc Video Finishing vừa hoàn tất")
        final_path = None
        return _operation_response(completed)
    except asyncio.CancelledError:
        _safe_unlink(final_path)
        _mark_failed(operation_id, account_id, request=request, code="VIDEO_TRANSFORM_CANCELLED")
        raise
    except VideoTransformError as exc:
        _safe_unlink(final_path)
        if exc.code == "VIDEO_TRANSFORM_SOURCE_UNAVAILABLE" and active_source_id:
            _mark_source_unavailable(active_source_id, account_id)
        _mark_failed(operation_id, account_id, request=request, code=exc.code)
        raise HTTPException(status_code=_error_status(exc.code), detail=exc.public_message) from exc
    except HTTPException as exc:
        _safe_unlink(final_path)
        _mark_failed(
            operation_id,
            account_id,
            request=request,
            code="VIDEO_TRANSFORM_QUOTA" if exc.status_code == 413 else "VIDEO_TRANSFORM_REQUEST",
        )
        raise
    except Exception as exc:
        _safe_unlink(final_path)
        _mark_failed(operation_id, account_id, request=request, code="VIDEO_TRANSFORM_OPERATION")
        raise HTTPException(status_code=500, detail="Không thể hoàn thiện video an toàn") from exc
    finally:
        _safe_unlink(source_staging)
        _safe_unlink(rendered)
        if capacity_reserved:
            media_ffmpeg_capacity().release()


async def download_video_transform_operation(operation_id: str, account: dict):
    """Deliver one owner-only verified transform as a sealed temporary stream."""

    # Resolve the attested runtime once before touching the completed receipt.
    # A transient host problem must not mutate or remove a user's artifact.
    _, ffprobe = _require_runtime()
    operation_id = _uuid(operation_id, label="Mã Video Finishing")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with transaction() as conn:
        operation = _operation_for_account(conn, operation_id, account_id)
    if operation is None or str(operation[4]) not in {"completed", "unavailable"}:
        return _operation_not_found()
    if str(operation[4]) != "completed":
        return _operation_unavailable()
    path: Path | None = None
    download_capacity_reserved = False
    handoff = _SealedVideoTransformPreparation()
    try:
        if str(operation[25] or "") != "video/mp4":
            raise VideoTransformError("Video Finishing có MIME không hợp lệ", code="VIDEO_TRANSFORM_OUTPUT_INVALID")
        path, byte_size, digest, width, height, expected_duration, expected_audio = _completed_output_details(operation)
        # Verification reads and probes the entire private artifact. Reserve
        # this bounded slot before that work, not merely before streaming.
        _reserve_download_capacity()
        download_capacity_reserved = True
        await run_in_threadpool(
            _verify_mp4_output,
            path,
            ffprobe=ffprobe,
            expected_width=width,
            expected_height=height,
            expected_duration_seconds=expected_duration,
            expected_audio=expected_audio,
            expected_bytes=byte_size,
            expected_digest=digest,
        )
    except asyncio.CancelledError:
        handoff.cancel()
        if download_capacity_reserved:
            _release_download_capacity()
        raise
    except VideoTransformError as exc:
        handoff.cancel()
        if download_capacity_reserved:
            _release_download_capacity()
        if exc.code in {"VIDEO_TRANSFORM_RUNTIME_UNAVAILABLE", "VIDEO_TRANSFORM_PROBE_TIMEOUT"}:
            raise HTTPException(status_code=_error_status(exc.code), detail=exc.public_message) from exc
        if exc.code == "VIDEO_TRANSFORM_OUTPUT_LIMIT":
            # A later policy reduction must not destroy a completed private
            # artifact. Keep the receipt intact so an operator can restore a
            # compatible limit or perform a deliberate retention action.
            return envelope(
                False,
                "Video Finishing vượt giới hạn tải hiện tại; dữ liệu riêng tư vẫn được giữ an toàn.",
                status_name="guarded",
                error_code="VIDEO_TRANSFORM_OUTPUT_LIMIT",
            )
        _mark_output_unavailable(operation_id, account_id)
        _safe_unlink(path)
        return _operation_unavailable()
    except (OSError, RuntimeError) as exc:
        handoff.cancel()
        if download_capacity_reserved:
            _release_download_capacity()
        raise HTTPException(
            status_code=503,
            detail="Video Finishing chưa thể xác minh tệp riêng tư để tải an toàn. Vui lòng thử lại sau.",
        ) from exc
    try:
        sealed_stream = await run_in_threadpool(
            _prepare_sealed_output_for_handoff,
            handoff,
            path,
            expected_bytes=byte_size,
            expected_digest=digest,
        )
    except asyncio.CancelledError:
        handoff.cancel()
        if download_capacity_reserved:
            _release_download_capacity()
        raise
    except _SealedVideoTransformDeliveryError:
        handoff.cancel()
        if download_capacity_reserved:
            _release_download_capacity()
        return envelope(
            False,
            "Không thể chuẩn bị Video Finishing riêng tư để tải an toàn. Vui lòng thử lại.",
            status_name="guarded",
            error_code="VIDEO_TRANSFORM_DELIVERY_UNAVAILABLE",
        )
    except Exception:
        handoff.cancel()
        if download_capacity_reserved:
            _release_download_capacity()
        raise
    if sealed_stream is None:
        handoff.cancel()
        if download_capacity_reserved:
            _release_download_capacity()
        _mark_output_unavailable(operation_id, account_id)
        _safe_unlink(path)
        return _operation_unavailable()
    sealed_stream = handoff.detach()
    if sealed_stream is None:
        if download_capacity_reserved:
            _release_download_capacity()
        return envelope(
            False,
            "Không thể chuẩn bị Video Finishing riêng tư để tải an toàn. Vui lòng thử lại.",
            status_name="guarded",
            error_code="VIDEO_TRANSFORM_DELIVERY_UNAVAILABLE",
        )
    finalizer = _sealed_download_finalizer(sealed_stream)
    # Ownership of both the temporary stream and the semaphore is transferred
    # to the response finalizer at this point.
    download_capacity_reserved = False
    try:
        return _attachment_response(
            sealed_stream,
            byte_size=byte_size,
            filename=str(operation[24] or "toan-aas-video-finished.mp4"),
            on_close=finalizer,
        )
    except BaseException:
        finalizer()
        raise


@router.get("/{operation_id}/download")
async def download_video_transform_operation_route(operation_id: str, account: dict = Depends(require_account)):
    return await download_video_transform_operation(operation_id, account)


@router.get("/{operation_id}")
async def get_video_transform_operation(operation_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã Video Finishing")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with transaction() as conn:
        operation = _operation_for_account(conn, operation_id, account_id)
        events = conn.execute(
            """SELECT state, created_at FROM web_video_transform_operation_events
               WHERE operation_id=? ORDER BY sequence ASC, id ASC LIMIT 60""",
            (operation_id,),
        ).fetchall()
    if operation is None:
        return _operation_not_found()
    public = _public_operation(operation)
    return envelope(
        True,
        "Đã tải trạng thái Video Finishing riêng tư.",
        data={
            "operation": public,
            "events": [{"state": str(event[0]), "created_at": str(event[1])} for event in events],
        },
        status_name=str(public["state"]),
    )


def _parse_reconciliation_fence(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone")
        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
    except ValueError as exc:
        raise RuntimeError("Startup Video Finishing reconciliation fence không hợp lệ") from exc


def _clear_old_files(directory: Path, *, known_names: set[str], now: datetime) -> None:
    """Remove only stale regular orphan files below a verified private root."""

    try:
        children = list(directory.iterdir())
    except OSError:
        return
    cutoff = now.timestamp() - ORPHAN_RETENTION_SECONDS
    for path in children:
        try:
            if path.name in known_names or not path.is_file() or path.is_symlink() or path.stat().st_mtime > cutoff:
                continue
            path.unlink()
        except OSError:
            continue


def reconcile_video_transform_operation_storage(*, interrupted_before: str | None = None) -> None:
    """Fail closed for interrupted/corrupt work and stale operation-local files."""

    if not video_transform_operations_enabled():
        return
    ensure_copyfast_schema()
    root = _feature_root()
    outputs = _private_directory(root, "outputs")
    staging = _private_directory(root, ".staging")
    _, ffprobe = _runtime()
    fence = _parse_reconciliation_fence(interrupted_before)
    with transaction() as conn:
        rows = conn.execute(
            f"SELECT {OPERATION_SELECT} FROM web_video_transform_operations"
        ).fetchall()
    referenced_names: set[str] = set()
    for row in rows:
        operation = tuple(row)
        try:
            operation_id = str(operation[0])
            account_id = str(operation[1])
            state = str(operation[4])
        except (IndexError, TypeError, ValueError):
            continue
        if state in {"queued", "processing"}:
            activity = str(operation[31] or operation[30] or operation[29] or "")
            if not fence or (activity and activity < fence):
                _mark_failed(operation_id, account_id, request=None, code="VIDEO_TRANSFORM_INTERRUPTED")
            continue
        if state != "completed":
            continue
        try:
            path, byte_size, digest, width, height, duration, has_audio = _completed_output_details(operation)
            referenced_names.add(path.name)
            _verify_mp4_output(
                path,
                ffprobe=ffprobe,
                expected_width=width,
                expected_height=height,
                expected_duration_seconds=duration,
                expected_audio=has_audio,
                expected_bytes=byte_size,
                expected_digest=digest,
            )
        except (VideoTransformError, OSError, RuntimeError):
            _mark_output_unavailable(operation_id, account_id)
    now = datetime.now(timezone.utc)
    _clear_old_files(outputs, known_names=referenced_names, now=now)
    _clear_old_files(staging, known_names=set(), now=now)
