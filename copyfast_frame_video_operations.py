"""Bounded, private Frame Video Lab for the standalone Web App.

This Web-native module turns an ordered set of 2–8 immutable Asset Vault
images into one verified H.264 MP4.  It intentionally does not emulate the
Telegram Bot's mutable session, local-worker path hand-off, billing, wallet,
provider, notification or Telegram delivery behaviour.  The browser supplies
only opaque Asset Vault IDs and a small closed render specification; every
path, decoder setting, FFmpeg argument and delivery stream is server-owned.
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
import warnings

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator
from starlette.concurrency import run_in_threadpool

from copyfast_assets import open_verified_private_asset_stream
from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import (
    asset_vault_enabled,
    ensure_copyfast_schema,
    frame_video_operations_directory,
    frame_video_operations_enabled,
    transaction,
    utc_now,
)
from copyfast_image_runtime import image_decoder_capacity
from copyfast_media_runtime import media_ffmpeg_capacity


router = APIRouter(prefix="/api/v1/frame-video-operations", tags=["Frame Video Lab"])

FRAME_VIDEO_KIND = "frame_video"
STATE_VALUES = frozenset({"queued", "processing", "completed", "failed", "guarded", "unavailable"})
ASPECT_RATIOS = {
    "9:16": (720, 1280),
    "16:9": (1280, 720),
    "1:1": (1080, 1080),
    "4:5": (864, 1080),
}
SECONDS_PER_IMAGE_VALUES = frozenset({1.5, 3.0, 4.0})
REQUESTED_EFFECTS = frozenset({"none", "fade", "zoom", "pan", "slide", "random"})
CONCRETE_EFFECTS = ("none", "fade", "zoom", "pan", "slide")
IMAGE_MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
ASSET_STORAGE_KEY_PATTERN = re.compile(r"^objects/[0-9a-f]{32}\.blob$")
OUTPUT_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.mp4$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

CHUNK_BYTES = 1024 * 1024
MAX_SOURCE_COUNT = 8
MIN_SOURCE_COUNT = 2
MAX_SOURCE_BYTES = 10 * 1024 * 1024
MAX_SOURCE_TOTAL_BYTES = 30 * 1024 * 1024
MAX_SOURCE_DIMENSION = 6_144
MAX_SOURCE_PIXELS = 12 * 1024 * 1024
MAX_SOURCE_ASPECT = 12.0
MAX_OUTPUT_SECONDS = 24.0
MAX_OUTPUT_PIXELS = 1_600_000
OUTPUT_FPS = 30
RENDER_TIMEOUT_SECONDS = 60.0
PROBE_TIMEOUT_SECONDS = 8.0
ORPHAN_RETENTION_SECONDS = 60 * 60
FRAME_VIDEO_TOPOLOGY_SQLITE_SINGLE_REPLICA = "sqlite_single_replica"
REPLICA_COUNT_ENV_NAMES = ("RAILWAY_REPLICA_COUNT", "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT")
_DOWNLOAD_CAPACITY = threading.BoundedSemaphore(value=2)

OPERATION_SELECT = """id, account_id, kind, state, idempotency_key, request_fingerprint,
                      aspect_ratio, seconds_per_image, effect, source_count, source_total_bytes,
                      output_duration_ms, output_width, output_height, storage_key,
                      original_filename, content_type, byte_size, sha256, failure_code,
                      created_at, queued_at, started_at, completed_at, updated_at, revision"""
SOURCE_SELECT = """id, operation_id, source_asset_id, source_index, source_sha256,
                   source_byte_size, source_extension, source_content_type, created_at"""


class FrameVideoError(Exception):
    """A bounded failure whose message is safe for the signed owner."""

    def __init__(self, message: str, *, code: str = "FRAME_VIDEO_INVALID"):
        super().__init__(message)
        self.public_message = message
        self.code = code


class _SealedFrameVideoDeliveryError(RuntimeError):
    """A transient private delivery snapshot failure, not artifact corruption."""


class _SealedFrameVideoStreamingResponse(StreamingResponse):
    """Always release a sealed MP4 stream, including on client disconnect."""

    def __init__(self, content: Iterator[bytes], *, on_close: Callable[[], None], **kwargs: Any) -> None:
        self._sealed_frame_video_on_close = on_close
        super().__init__(content, **kwargs)

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._sealed_frame_video_on_close()


class _FrameVideoSpec(BaseModel):
    """Closed, browser-safe render inputs shared by estimate and creation."""

    model_config = ConfigDict(extra="forbid")

    source_asset_ids: list[StrictStr] = Field(min_length=MIN_SOURCE_COUNT, max_length=MAX_SOURCE_COUNT)
    aspect_ratio: StrictStr = Field(default="9:16", min_length=3, max_length=4)
    seconds_per_image: float = Field(default=3.0)
    effect: StrictStr = Field(default="fade", min_length=3, max_length=8)

    @field_validator("source_asset_ids")
    @classmethod
    def validate_source_asset_ids(cls, value: list[StrictStr]) -> list[str]:
        if not isinstance(value, list) or not (MIN_SOURCE_COUNT <= len(value) <= MAX_SOURCE_COUNT):
            raise ValueError("Frame Video cần từ 2 đến 8 ảnh Asset Vault")
        normalized = [_uuid(str(item), label="Asset Vault ID") for item in value]
        if len(set(normalized)) != len(normalized):
            raise ValueError("Mỗi ảnh Asset Vault chỉ được chọn một lần")
        return normalized

    @field_validator("aspect_ratio")
    @classmethod
    def validate_aspect_ratio(cls, value: StrictStr) -> str:
        candidate = str(value or "").strip()
        if candidate not in ASPECT_RATIOS:
            raise ValueError("Tỷ lệ chỉ nhận 9:16, 16:9, 1:1 hoặc 4:5")
        return candidate

    @field_validator("seconds_per_image", mode="before")
    @classmethod
    def validate_seconds_type(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Thời lượng mỗi ảnh phải là số")
        normalized = float(value)
        if normalized not in SECONDS_PER_IMAGE_VALUES:
            raise ValueError("Thời lượng mỗi ảnh chỉ nhận 1.5, 3 hoặc 4 giây")
        return normalized

    @field_validator("effect")
    @classmethod
    def validate_effect(cls, value: StrictStr) -> str:
        candidate = str(value or "").strip().lower()
        if candidate not in REQUESTED_EFFECTS:
            raise ValueError("Hiệu ứng chỉ nhận none, fade, zoom, pan, slide hoặc random")
        return candidate


class FrameVideoEstimateRequest(_FrameVideoSpec):
    """A non-mutating render plan for the signed owner's own source assets."""


class FrameVideoRequest(_FrameVideoSpec):
    """One immutable ordered source snapshot becomes one private MP4."""

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
    return frame_video_operations_enabled() and asset_vault_enabled()


def _require_enabled() -> None:
    if not _feature_enabled():
        raise HTTPException(
            status_code=503,
            detail="Frame Video Lab cần Asset Vault private và WEBAPP_FRAME_VIDEO_OPERATIONS_ENABLED=true",
        )


def _topology_guarded_code() -> str | None:
    """Block the in-request SQLite executor outside one attested replica."""

    topology = os.environ.get("WEBAPP_FRAME_VIDEO_OPERATIONS_TOPOLOGY", "").strip().lower()
    if not topology:
        # The existing bounded local media family already uses this operator
        # setting. Reusing only its explicit topology value does not enable
        # Poster or share its storage/database surface.
        topology = os.environ.get("WEBAPP_VIDEO_OPERATIONS_TOPOLOGY", "").strip().lower()
    if topology != FRAME_VIDEO_TOPOLOGY_SQLITE_SINGLE_REPLICA:
        return "FRAME_VIDEO_TOPOLOGY_UNVERIFIED"
    attested = False
    for name in REPLICA_COUNT_ENV_NAMES:
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        attested = True
        try:
            replicas = int(raw)
        except ValueError:
            return "FRAME_VIDEO_REPLICA_COUNT_UNVERIFIED"
        if replicas != 1:
            return "FRAME_VIDEO_MULTI_REPLICA_BLOCKED"
    return None if attested else "FRAME_VIDEO_REPLICA_COUNT_UNVERIFIED"


def _binary_path(primary_environment_name: str, fallback_environment_name: str, expected_name: str) -> str:
    """Resolve an explicit trusted binary; browser input never reaches this."""

    configured = os.environ.get(primary_environment_name, "").strip() or os.environ.get(fallback_environment_name, "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise FrameVideoError("Runtime Frame Video chưa có binary tuyệt đối đã kiểm định", code="FRAME_VIDEO_RUNTIME_UNAVAILABLE")
    else:
        discovered = shutil.which(expected_name)
        if not discovered:
            raise FrameVideoError("Runtime Frame Video chưa có FFmpeg/ffprobe", code="FRAME_VIDEO_RUNTIME_UNAVAILABLE")
        candidate = Path(discovered)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise FrameVideoError("Runtime Frame Video chưa có binary hợp lệ", code="FRAME_VIDEO_RUNTIME_UNAVAILABLE") from exc
    accepted_names = {expected_name.lower(), f"{expected_name}.exe".lower()}
    if resolved.name.lower() not in accepted_names or not resolved.is_file():
        raise FrameVideoError("Runtime Frame Video chưa có binary hợp lệ", code="FRAME_VIDEO_RUNTIME_UNAVAILABLE")
    if os.name != "nt" and not os.access(resolved, os.X_OK):
        raise FrameVideoError("Runtime Frame Video chưa có binary có thể chạy", code="FRAME_VIDEO_RUNTIME_UNAVAILABLE")
    return str(resolved)


def _runtime() -> tuple[str, str]:
    return (
        _binary_path("WEBAPP_FRAME_VIDEO_FFMPEG_BIN", "WEBAPP_VIDEO_FFMPEG_BIN", "ffmpeg"),
        _binary_path("WEBAPP_FRAME_VIDEO_FFPROBE_BIN", "WEBAPP_VIDEO_FFPROBE_BIN", "ffprobe"),
    )


def ensure_frame_video_operations_runtime() -> None:
    """Fail closed during startup only when Frame Video was explicitly enabled."""

    if not frame_video_operations_enabled():
        return
    if not asset_vault_enabled():
        raise RuntimeError("Frame Video Lab cần WEBAPP_ASSET_VAULT_ENABLED=true")
    if _topology_guarded_code():
        raise RuntimeError("Frame Video Lab cần topology SQLite single-replica đã được xác nhận")
    _runtime()


def _require_runtime() -> tuple[str, str]:
    _require_enabled()
    if _topology_guarded_code():
        raise HTTPException(
            status_code=503,
            detail="Frame Video Lab chỉ chạy trên topology SQLite single-replica đã được xác nhận.",
        )
    try:
        return _runtime()
    except FrameVideoError as exc:
        raise HTTPException(status_code=503, detail=exc.public_message) from exc


def _maximum_output_bytes() -> int:
    raw = os.environ.get("WEBAPP_FRAME_VIDEO_MAX_OUTPUT_MB", "25").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 25
    return max(1, min(megabytes, 100)) * 1024 * 1024


def _maximum_account_bytes() -> int:
    raw = os.environ.get("WEBAPP_FRAME_VIDEO_QUOTA_MB", "250").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 250
    return max(1, min(megabytes, 5_000)) * 1024 * 1024


def _feature_root() -> Path:
    root = frame_video_operations_directory()
    if root.exists() and root.is_symlink():
        raise RuntimeError("Storage Frame Video không được là symbolic link")
    return root.resolve()


def _private_directory(root: Path, name: str) -> Path:
    if name not in {".staging", "outputs"}:
        raise RuntimeError("Thư mục Frame Video không hợp lệ")
    candidate = root.resolve() / name
    if candidate.exists() and candidate.is_symlink():
        raise RuntimeError("Thư mục Frame Video không được là symbolic link")
    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise RuntimeError("Thư mục Frame Video không hợp lệ")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError("Thư mục Frame Video vượt ngoài storage riêng") from exc
    return resolved


def _staging_path(root: Path, suffix: str) -> Path:
    return _private_directory(root, ".staging") / f"{uuid.uuid4().hex}{suffix}"


def _output_path(root: Path, storage_key: str) -> Path:
    if not OUTPUT_STORAGE_KEY_PATTERN.fullmatch(str(storage_key or "")):
        raise RuntimeError("Storage key Frame Video không hợp lệ")
    private_root = root.resolve()
    candidate = private_root / str(storage_key)
    try:
        candidate.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError("Storage key Frame Video vượt ngoài storage riêng") from exc
    return candidate


def _safe_unlink(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.is_file() and not path.is_symlink():
            path.unlink()
    except OSError:
        pass


def _safe_unlink_all(paths: list[Path]) -> None:
    for path in paths:
        _safe_unlink(path)


def _source_row_for_account(conn: Any, *, source_asset_id: str, account_id: str):
    return conn.execute(
        """SELECT id, extension, content_type, byte_size, sha256, storage_key, state
           FROM web_asset_files WHERE id=? AND account_id=?""",
        (source_asset_id, account_id),
    ).fetchone()


def _source_snapshot_from_row(row: tuple[Any, ...] | Any) -> dict[str, Any] | None:
    if not row:
        return None
    try:
        asset_id = str(row[0])
        extension = str(row[1] or "").lower()
        content_type = str(row[2] or "").lower()
        byte_size = int(row[3])
        digest = str(row[4] or "").lower()
        storage_key = str(row[5] or "")
        state = str(row[6] or "")
    except (IndexError, TypeError, ValueError):
        return None
    if (
        not UUID_PATTERN.fullmatch(asset_id)
        or extension not in IMAGE_MIME_BY_EXTENSION
        or content_type != IMAGE_MIME_BY_EXTENSION[extension]
        or byte_size < 1
        or byte_size > MAX_SOURCE_BYTES
        or SHA256_PATTERN.fullmatch(digest) is None
        or ASSET_STORAGE_KEY_PATTERN.fullmatch(storage_key) is None
        or state != "active"
    ):
        return None
    return {
        "id": str(uuid.UUID(asset_id)),
        "extension": extension,
        "content_type": content_type,
        "byte_size": byte_size,
        "sha256": digest,
        "storage_key": storage_key,
    }


def _sources_for_account(conn: Any, *, source_asset_ids: list[str], account_id: str) -> list[dict[str, Any]] | None:
    snapshots: list[dict[str, Any]] = []
    total = 0
    for source_asset_id in source_asset_ids:
        snapshot = _source_snapshot_from_row(
            _source_row_for_account(conn, source_asset_id=source_asset_id, account_id=account_id)
        )
        if snapshot is None:
            return None
        total += int(snapshot["byte_size"])
        if total > MAX_SOURCE_TOTAL_BYTES:
            raise HTTPException(status_code=413, detail="Tổng dung lượng ảnh Frame Video vượt giới hạn 30 MB")
        snapshots.append(snapshot)
    return snapshots


def _source_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Một hoặc nhiều ảnh Asset Vault không còn sẵn sàng cho Frame Video.",
        status_name="guarded",
        error_code="FRAME_VIDEO_SOURCE_UNAVAILABLE",
    )


def _operation_not_found() -> dict[str, Any]:
    return envelope(False, "Không tìm thấy Frame Video riêng tư.", status_name="guarded", error_code="FRAME_VIDEO_NOT_FOUND")


def _operation_unavailable() -> dict[str, Any]:
    return envelope(
        False,
        "Frame Video không còn vượt qua kiểm tra integrity để sử dụng.",
        status_name="unavailable",
        error_code="FRAME_VIDEO_OUTPUT_UNAVAILABLE",
    )


def _normalized_spec(payload: _FrameVideoSpec) -> dict[str, Any]:
    width, height = ASPECT_RATIOS[str(payload.aspect_ratio)]
    seconds = float(payload.seconds_per_image)
    return {
        "aspect_ratio": str(payload.aspect_ratio),
        "seconds_per_image": seconds,
        "effect": str(payload.effect),
        "width": width,
        "height": height,
        "duration_seconds": round(len(payload.source_asset_ids) * seconds, 3),
    }


def _request_fingerprint(*, source_snapshots: list[dict[str, Any]], spec: dict[str, Any]) -> str:
    payload = {
        "kind": FRAME_VIDEO_KIND,
        "sources": [
            {
                "id": str(source["id"]),
                "sha256": str(source["sha256"]),
                "byte_size": int(source["byte_size"]),
                "extension": str(source["extension"]),
                "content_type": str(source["content_type"]),
            }
            for source in source_snapshots
        ],
        "spec": {
            "aspect_ratio": str(spec["aspect_ratio"]),
            "seconds_per_image": float(spec["seconds_per_image"]),
            "effect": str(spec["effect"]),
        },
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _effective_effect(effect: str, fingerprint: str) -> str:
    if effect != "random":
        return effect
    # Random is stable for an idempotent immutable request; it never calls a
    # provider or leaves a non-reproducible render choice in server state.
    index = int(hashlib.sha256(fingerprint.encode("ascii")).hexdigest()[:8], 16) % len(CONCRETE_EFFECTS)
    return CONCRETE_EFFECTS[index]


def _record_event(conn: Any, *, operation_id: str, state: str, when: str | None = None) -> None:
    now = when or utc_now()
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 FROM web_frame_video_operation_events WHERE operation_id=?",
        (operation_id,),
    ).fetchone()
    sequence = int(row[0] or 1) if row else 1
    conn.execute(
        """INSERT INTO web_frame_video_operation_events (id, operation_id, state, sequence, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), operation_id, state, sequence, now),
    )


def _sources_for_operation(conn: Any, operation_id: str) -> list[tuple[Any, ...]]:
    rows = conn.execute(
        f"""SELECT {SOURCE_SELECT} FROM web_frame_video_operation_sources
            WHERE operation_id=? ORDER BY source_index ASC, id ASC""",
        (operation_id,),
    ).fetchall()
    return [tuple(row) for row in rows]


def _operation_for_account(conn: Any, operation_id: str, account_id: str) -> tuple[Any, ...] | None:
    row = conn.execute(
        f"SELECT {OPERATION_SELECT} FROM web_frame_video_operations WHERE id=? AND account_id=?",
        (operation_id, account_id),
    ).fetchone()
    return tuple(row) if row else None


def _snapshot_from_source_rows(rows: list[tuple[Any, ...]]) -> list[dict[str, Any]] | None:
    snapshots: list[dict[str, Any]] = []
    for expected_index, row in enumerate(rows):
        try:
            source_index = int(row[3])
            source_id = str(row[2])
            digest = str(row[4] or "").lower()
            byte_size = int(row[5])
            extension = str(row[6] or "").lower()
            content_type = str(row[7] or "").lower()
        except (IndexError, TypeError, ValueError):
            return None
        if (
            source_index != expected_index
            or UUID_PATTERN.fullmatch(source_id) is None
            or SHA256_PATTERN.fullmatch(digest) is None
            or extension not in IMAGE_MIME_BY_EXTENSION
            or content_type != IMAGE_MIME_BY_EXTENSION[extension]
            or byte_size < 1
            or byte_size > MAX_SOURCE_BYTES
        ):
            return None
        snapshots.append(
            {
                "id": str(uuid.UUID(source_id)),
                "sha256": digest,
                "byte_size": byte_size,
                "extension": extension,
                "content_type": content_type,
            }
        )
    return snapshots if MIN_SOURCE_COUNT <= len(snapshots) <= MAX_SOURCE_COUNT else None


def _replay_matches(operation: tuple[Any, ...], rows: list[tuple[Any, ...]], payload: FrameVideoRequest) -> bool:
    try:
        if str(operation[2]) != FRAME_VIDEO_KIND:
            return False
        spec = {
            "aspect_ratio": str(operation[6]),
            "seconds_per_image": float(operation[7]),
            "effect": str(operation[8]),
        }
        if (
            spec["aspect_ratio"] != str(payload.aspect_ratio)
            or spec["seconds_per_image"] != float(payload.seconds_per_image)
            or spec["effect"] != str(payload.effect)
            or int(operation[9]) != len(payload.source_asset_ids)
        ):
            return False
    except (IndexError, TypeError, ValueError):
        return False
    snapshots = _snapshot_from_source_rows(rows)
    if snapshots is None or [str(item["id"]) for item in snapshots] != list(payload.source_asset_ids):
        return False
    fingerprint = _request_fingerprint(source_snapshots=snapshots, spec=spec)
    return hmac.compare_digest(str(operation[5] or ""), fingerprint)


def _public_operation(operation: tuple[Any, ...]) -> dict[str, Any]:
    try:
        state = str(operation[3])
        fingerprint = str(operation[5] or "")
        effect = str(operation[8])
        byte_size = int(operation[17]) if operation[17] is not None else None
        width = int(operation[12]) if operation[12] is not None else None
        height = int(operation[13]) if operation[13] is not None else None
        duration_ms = int(operation[11]) if operation[11] is not None else None
    except (IndexError, TypeError, ValueError):
        raise FrameVideoError("Receipt Frame Video không hợp lệ", code="FRAME_VIDEO_RECEIPT_INVALID")
    return {
        "id": str(operation[0]),
        "kind": FRAME_VIDEO_KIND,
        "state": state if state in STATE_VALUES else "guarded",
        "aspect_ratio": str(operation[6]),
        "seconds_per_image": float(operation[7]),
        "effect": effect,
        "effective_effect": _effective_effect(effect, fingerprint) if SHA256_PATTERN.fullmatch(fingerprint) else None,
        "source_count": int(operation[9]),
        "source_total_bytes": int(operation[10]),
        "output": {
            "available": state == "completed" and byte_size is not None,
            "filename": str(operation[15]) if operation[15] else None,
            "content_type": str(operation[16]) if operation[16] else None,
            "byte_size": byte_size,
            "duration_ms": duration_ms,
            "width": width,
            "height": height,
        },
        "failure_code": str(operation[19]) if operation[19] else None,
        "created_at": str(operation[20]),
        "queued_at": str(operation[21]),
        "started_at": str(operation[22]) if operation[22] else None,
        "completed_at": str(operation[23]) if operation[23] else None,
        "updated_at": str(operation[24]),
    }


def _operation_response(operation: tuple[Any, ...], *, replay: bool = False) -> dict[str, Any]:
    public = _public_operation(operation)
    state = str(public["state"])
    return envelope(
        True,
        "Đã dùng lại Frame Video trước đó." if replay else "Frame Video đã được tạo và kiểm tra riêng tư.",
        data={"operation": public, "replay": replay},
        status_name=state,
    )


def _error_status(code: str) -> int:
    if code.endswith("_TIMEOUT"):
        return 504
    if code in {"FRAME_VIDEO_RUNTIME_UNAVAILABLE", "FRAME_VIDEO_TOPOLOGY_UNVERIFIED"}:
        return 503
    if code.endswith("_LIMIT") or code.endswith("_TOO_LARGE"):
        return 413
    if code.endswith("_UNAVAILABLE"):
        return 409
    return 422


def _quota_available(conn: Any, *, account_id: str, additional_bytes: int) -> bool:
    row = conn.execute(
        """SELECT COALESCE(SUM(byte_size), 0) FROM web_frame_video_operations
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
            "SELECT state FROM web_frame_video_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
        if not row or str(row[0]) not in {"queued", "processing"}:
            return
        conn.execute(
            """UPDATE web_frame_video_operations
               SET state='failed', failure_code=?, updated_at=?, revision=revision + 1
               WHERE id=? AND account_id=? AND state IN ('queued', 'processing')""",
            (code[:96], now, operation_id, account_id),
        )
        conn.execute(
            """UPDATE web_frame_video_operation_attempts
               SET state='failed', completed_at=?, failure_code=?
               WHERE operation_id=? AND account_id=? AND state='processing'""",
            (now, code[:96], operation_id, account_id),
        )
        _record_event(conn, operation_id=operation_id, state="failed", when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.frame_video.failed",
            request_id=_request_id(request) if request is not None else "startup",
            target=operation_id,
            detail=f"code={code[:80]}",
        )


def _mark_output_unavailable(operation_id: str, account_id: str) -> None:
    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            "SELECT state FROM web_frame_video_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
        if not row or str(row[0]) != "completed":
            return
        conn.execute(
            """UPDATE web_frame_video_operations
               SET state='unavailable', failure_code='FRAME_VIDEO_OUTPUT_UNAVAILABLE', updated_at=?, revision=revision + 1
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


def _image_classes():
    try:
        from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError
    except ImportError as exc:  # pragma: no cover - deployment configuration
        raise FrameVideoError("Runtime Frame Video chưa có Pillow an toàn", code="FRAME_VIDEO_RUNTIME_UNAVAILABLE") from exc
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    return Image, ImageFile, ImageOps, UnidentifiedImageError


def _format_matches(extension: str, image_format: str | None) -> bool:
    expected = {
        ".jpg": {"JPEG"},
        ".jpeg": {"JPEG"},
        ".png": {"PNG"},
        ".webp": {"WEBP"},
    }.get(extension, set())
    return str(image_format or "").upper() in expected


def _image_magic_matches(extension: str, prefix: bytes) -> bool:
    if extension == ".png":
        return prefix.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return prefix.startswith(b"\xff\xd8\xff")
    if extension == ".webp":
        return len(prefix) >= 12 and prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP"
    return False


def _validate_source_geometry(width: int, height: int) -> None:
    if width < 1 or height < 1:
        raise FrameVideoError("Kích thước ảnh Frame Video không hợp lệ", code="FRAME_VIDEO_DIMENSION_LIMIT")
    if width > MAX_SOURCE_DIMENSION or height > MAX_SOURCE_DIMENSION:
        raise FrameVideoError(
            f"Cạnh dài ảnh Frame Video vượt giới hạn {MAX_SOURCE_DIMENSION} px",
            code="FRAME_VIDEO_DIMENSION_LIMIT",
        )
    if width * height > MAX_SOURCE_PIXELS:
        raise FrameVideoError("Độ phân giải ảnh Frame Video vượt giới hạn xử lý an toàn", code="FRAME_VIDEO_DIMENSION_LIMIT")
    if max(width, height) / min(width, height) > MAX_SOURCE_ASPECT:
        raise FrameVideoError("Tỷ lệ ảnh Frame Video vượt giới hạn xử lý an toàn", code="FRAME_VIDEO_DIMENSION_LIMIT")


def _copy_verified_image_source(destination: Path, *, source: dict[str, Any]) -> None:
    """Copy one descriptor-pinned Vault source into an isolated staging file."""

    stream = open_verified_private_asset_stream(
        storage_key=str(source["storage_key"]),
        expected_bytes=int(source["byte_size"]),
        expected_digest=str(source["sha256"]),
    )
    if stream is None:
        raise FrameVideoError("Ảnh nguồn không còn vượt qua kiểm tra integrity", code="FRAME_VIDEO_SOURCE_UNAVAILABLE")
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
                        raise FrameVideoError("Ảnh nguồn vượt giới hạn 10 MB", code="FRAME_VIDEO_SOURCE_TOO_LARGE")
                    if len(prefix) < 32:
                        prefix.extend(chunk[: 32 - len(prefix)])
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        except FrameVideoError:
            raise
        except OSError as exc:
            raise FrameVideoError("Không thể chuẩn bị ảnh Frame Video riêng tư", code="FRAME_VIDEO_STAGING_UNAVAILABLE") from exc
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            pass
    if (
        total != int(source["byte_size"])
        or not hmac.compare_digest(digest.hexdigest(), str(source["sha256"]))
        or not _image_magic_matches(str(source["extension"]), bytes(prefix))
    ):
        _safe_unlink(destination)
        raise FrameVideoError("Ảnh nguồn không còn vượt qua kiểm tra integrity", code="FRAME_VIDEO_SOURCE_UNAVAILABLE")


def _normalize_image_source(
    source_copy: Path,
    destination: Path,
    *,
    extension: str,
    target_width: int,
    target_height: int,
) -> None:
    """Decode once, check image safety, and write a server-owned JPEG input."""

    Image, ImageFile, ImageOps, UnidentifiedImageError = _image_classes()
    if ImageFile.LOAD_TRUNCATED_IMAGES:
        raise FrameVideoError("Image runtime không ở chế độ kiểm tra đầy đủ", code="FRAME_VIDEO_RUNTIME_UNAVAILABLE")
    canvas = None
    normalized = None
    converted = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source_copy) as verifier:
                if not _format_matches(extension, verifier.format):
                    raise FrameVideoError("Định dạng ảnh nguồn không khớp Asset Vault", code="FRAME_VIDEO_SOURCE_INVALID")
                if int(getattr(verifier, "n_frames", 1) or 1) != 1 or bool(getattr(verifier, "is_animated", False)):
                    raise FrameVideoError("Ảnh động chưa được hỗ trợ trong Frame Video", code="FRAME_VIDEO_ANIMATED")
                width, height = int(verifier.size[0]), int(verifier.size[1])
                try:
                    orientation = int(verifier.getexif().get(274, 1) or 1)
                except (AttributeError, TypeError, ValueError):
                    orientation = 1
                if orientation in {5, 6, 7, 8}:
                    width, height = height, width
                _validate_source_geometry(width, height)
                verifier.verify()
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source_copy) as decoded:
                if not _format_matches(extension, decoded.format):
                    raise FrameVideoError("Định dạng ảnh nguồn không khớp Asset Vault", code="FRAME_VIDEO_SOURCE_INVALID")
                if int(getattr(decoded, "n_frames", 1) or 1) != 1 or bool(getattr(decoded, "is_animated", False)):
                    raise FrameVideoError("Ảnh động chưa được hỗ trợ trong Frame Video", code="FRAME_VIDEO_ANIMATED")
                decoded.load()
                normalized = ImageOps.exif_transpose(decoded)
                converted = normalized.convert("RGBA")
                converted.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (target_width, target_height), (8, 15, 25))
                left = (target_width - converted.width) // 2
                top = (target_height - converted.height) // 2
                alpha = converted.getchannel("A")
                try:
                    canvas.paste(converted, (left, top), alpha)
                finally:
                    alpha.close()
                with destination.open("xb") as output:
                    canvas.save(output, format="JPEG", quality=92, optimize=False, progressive=False, subsampling=0)
                    output.flush()
                    os.fsync(output.fileno())
        if not destination.is_file() or destination.is_symlink() or destination.stat().st_size < 128:
            raise FrameVideoError("Không thể chuẩn bị ảnh Frame Video an toàn", code="FRAME_VIDEO_STAGING_UNAVAILABLE")
    except FrameVideoError:
        _safe_unlink(destination)
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        _safe_unlink(destination)
        raise FrameVideoError("Độ phân giải ảnh Frame Video vượt giới hạn xử lý an toàn", code="FRAME_VIDEO_DIMENSION_LIMIT") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        _safe_unlink(destination)
        raise FrameVideoError("Không thể decode ảnh Frame Video an toàn", code="FRAME_VIDEO_SOURCE_INVALID") from exc
    finally:
        if converted is not None:
            try:
                converted.close()
            except OSError:
                pass
        if normalized is not None:
            try:
                normalized.close()
            except OSError:
                pass
        if canvas is not None:
            try:
                canvas.close()
            except OSError:
                pass


def _effect_filter(
    input_index: int,
    *,
    effective_effect: str,
    width: int,
    height: int,
    seconds: float,
) -> str:
    """Return one fully server-generated FFmpeg filter chain for an image."""

    duration = f"{seconds:.3f}"
    base = f"[{input_index}:v]fps={OUTPUT_FPS},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x080f19,setsar=1"
    if effective_effect == "fade":
        fade_duration = min(0.25, max(0.05, seconds / 5.0))
        out_start = max(0.0, seconds - fade_duration)
        base += f",fade=t=in:st=0:d={fade_duration:.3f},fade=t=out:st={out_start:.3f}:d={fade_duration:.3f}"
    elif effective_effect == "zoom":
        base += f",scale=iw*1.06:ih*1.06,crop={width}:{height}:(in_w-out_w)/2:(in_h-out_h)/2"
    elif effective_effect == "pan":
        base += f",scale=iw*1.06:ih*1.06,crop={width}:{height}:x='(in_w-out_w)*min(1,t/{duration})':y='(in_h-out_h)/2'"
    elif effective_effect == "slide":
        extra = 96
        speed = extra / max(seconds, 0.1)
        base += f",pad={width + extra}:{height}:{extra}:0:color=0x080f19,crop={width}:{height}:x='min({extra},t*{speed:.6f})':y=0"
    return f"{base},trim=duration={duration},setpts=PTS-STARTPTS,format=yuv420p[v{input_index}]"


def _render_frame_video(
    ffmpeg: str,
    sources: list[Path],
    destination: Path,
    *,
    width: int,
    height: int,
    seconds_per_image: float,
    effective_effect: str,
) -> None:
    """Render an H.264 MP4 from server-normalized local JPEG staging files."""

    if not (MIN_SOURCE_COUNT <= len(sources) <= MAX_SOURCE_COUNT):
        raise FrameVideoError("Số ảnh Frame Video không hợp lệ", code="FRAME_VIDEO_INVALID")
    if effective_effect not in CONCRETE_EFFECTS:
        raise FrameVideoError("Hiệu ứng Frame Video không hợp lệ", code="FRAME_VIDEO_INVALID")
    command = [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-xerror", "-protocol_whitelist", "file,pipe"]
    for source in sources:
        # Source paths are opaque staging paths generated by this module,
        # never user supplied paths, URLs or arbitrary FFmpeg input strings.
        command.extend(["-loop", "1", "-framerate", str(OUTPUT_FPS), "-t", f"{seconds_per_image:.3f}", "-i", str(source)])
    chains = [
        _effect_filter(
            index,
            effective_effect=effective_effect,
            width=width,
            height=height,
            seconds=seconds_per_image,
        )
        for index in range(len(sources))
    ]
    concat_inputs = "".join(f"[v{index}]" for index in range(len(sources)))
    filter_graph = ";".join(chains + [f"{concat_inputs}concat=n={len(sources)}:v=1:a=0,format=yuv420p[outv]"])
    command.extend(
        [
            "-filter_complex",
            filter_graph,
            "-map",
            "[outv]",
            "-an",
            "-sn",
            "-dn",
            "-r",
            str(OUTPUT_FPS),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-f",
            "mp4",
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
        raise FrameVideoError("Tạo Frame Video vượt thời gian an toàn", code="FRAME_VIDEO_RENDER_TIMEOUT") from exc
    except OSError as exc:
        raise FrameVideoError("Không thể khởi động runtime Frame Video", code="FRAME_VIDEO_RUNTIME_UNAVAILABLE") from exc
    if completed.returncode != 0:
        raise FrameVideoError("Không thể tạo Frame Video từ các ảnh đã chọn", code="FRAME_VIDEO_RENDER_FAILED")


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
) -> int:
    """Verify exact bounded H.264/no-audio MP4 media facts with fixed argv."""

    command = [
        ffprobe,
        "-v",
        "error",
        "-protocol_whitelist",
        "file,pipe",
        "-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height,duration",
        "-of",
        "json",
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
        raise FrameVideoError("Kiểm tra Frame Video vượt thời gian an toàn", code="FRAME_VIDEO_PROBE_TIMEOUT") from exc
    except OSError as exc:
        raise FrameVideoError("Không thể khởi động kiểm tra Frame Video", code="FRAME_VIDEO_RUNTIME_UNAVAILABLE") from exc
    if completed.returncode != 0 or len(completed.stdout) > 16 * 1024:
        raise FrameVideoError("Frame Video không vượt qua kiểm tra định dạng", code="FRAME_VIDEO_OUTPUT_INVALID")
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FrameVideoError("Frame Video không vượt qua kiểm tra định dạng", code="FRAME_VIDEO_OUTPUT_INVALID") from exc
    streams = payload.get("streams") if isinstance(payload, dict) else None
    if not isinstance(streams, list):
        raise FrameVideoError("Frame Video không có stream hợp lệ", code="FRAME_VIDEO_OUTPUT_INVALID")
    videos = [stream for stream in streams if isinstance(stream, dict) and str(stream.get("codec_type") or "") == "video"]
    audios = [stream for stream in streams if isinstance(stream, dict) and str(stream.get("codec_type") or "") == "audio"]
    if len(videos) != 1 or audios:
        raise FrameVideoError("Frame Video đầu ra phải có đúng một video và không có audio", code="FRAME_VIDEO_OUTPUT_INVALID")
    video = videos[0]
    duration = _safe_float((payload.get("format") if isinstance(payload, dict) else {}).get("duration"))
    if duration is None:
        duration = _safe_float(video.get("duration"))
    width = _safe_int(video.get("width"))
    height = _safe_int(video.get("height"))
    if (
        str(video.get("codec_name") or "").lower() != "h264"
        or width != expected_width
        or height != expected_height
        or duration is None
        or duration <= 0
        or duration > MAX_OUTPUT_SECONDS
        or abs(duration - expected_duration_seconds) > max(0.75, expected_duration_seconds * 0.12)
    ):
        raise FrameVideoError("Frame Video đầu ra không khớp thông số đã xác nhận", code="FRAME_VIDEO_OUTPUT_INVALID")
    return int(round(duration * 1000))


def _verify_mp4_output(
    path: Path,
    *,
    ffprobe: str,
    expected_width: int,
    expected_height: int,
    expected_duration_seconds: float,
    expected_bytes: int | None = None,
    expected_digest: str | None = None,
) -> tuple[int, str, int]:
    """Verify file safety, byte integrity, MP4 magic and ffprobe media facts."""

    try:
        if not path.is_file() or path.is_symlink():
            raise FrameVideoError("Frame Video không còn integrity", code="FRAME_VIDEO_OUTPUT_INVALID")
        byte_size = int(path.stat().st_size)
        if byte_size < 128 or byte_size > _maximum_output_bytes():
            raise FrameVideoError("Frame Video vượt giới hạn lưu trữ", code="FRAME_VIDEO_OUTPUT_LIMIT")
        with path.open("rb") as stream:
            prefix = stream.read(16)
            stream.seek(0)
            digest = _digest_stream(stream)
        if len(prefix) < 12 or prefix[4:8] != b"ftyp":
            raise FrameVideoError("Frame Video không phải MP4 hợp lệ", code="FRAME_VIDEO_OUTPUT_INVALID")
        if expected_bytes is not None and byte_size != int(expected_bytes):
            raise FrameVideoError("Frame Video không còn integrity", code="FRAME_VIDEO_OUTPUT_INVALID")
        if expected_digest is not None and not hmac.compare_digest(digest, str(expected_digest)):
            raise FrameVideoError("Frame Video không còn integrity", code="FRAME_VIDEO_OUTPUT_INVALID")
        duration_ms = _probe_output(
            ffprobe,
            path,
            expected_width=expected_width,
            expected_height=expected_height,
            expected_duration_seconds=expected_duration_seconds,
        )
        return byte_size, digest, duration_ms
    except FrameVideoError:
        raise
    except OSError as exc:
        raise FrameVideoError("Frame Video không còn integrity", code="FRAME_VIDEO_OUTPUT_INVALID") from exc


def _publish_verified_output(root: Path, rendered: Path) -> tuple[Path, str]:
    """Atomically move a verified staging MP4 into the private output root."""

    outputs = _private_directory(root, "outputs")
    storage_key = f"outputs/{uuid.uuid4().hex}.mp4"
    final_path = _output_path(root, storage_key)
    if final_path.parent != outputs or final_path.exists():
        raise FrameVideoError("Không thể xuất Frame Video riêng tư", code="FRAME_VIDEO_STAGING_UNAVAILABLE")
    try:
        os.replace(rendered, final_path)
    except OSError as exc:
        raise FrameVideoError("Không thể xuất Frame Video riêng tư", code="FRAME_VIDEO_STAGING_UNAVAILABLE") from exc
    return final_path, storage_key


def _open_verified_output(path: Path, *, expected_bytes: int, expected_digest: str) -> BinaryIO | None:
    """Pin and hash one output descriptor without following a final symlink."""

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
        if len(prefix) < 12 or prefix[4:8] != b"ftyp":
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


def _seal_verified_output_for_delivery(
    stream: BinaryIO,
    *,
    expected_bytes: int,
    expected_digest: str,
) -> BinaryIO | None:
    """Make a rehashed anonymous snapshot before streaming private media."""

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
        raise _SealedFrameVideoDeliveryError("Không thể chuẩn bị luồng tải Frame Video private") from exc
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


def _reserve_download_capacity() -> None:
    if not _DOWNLOAD_CAPACITY.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Đang có nhiều lượt tải Frame Video private; vui lòng thử lại sau ít phút")


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
        raise ValueError("Kích thước Frame Video không hợp lệ")
    safe_name = str(filename or "toan-aas-frame-video.mp4").replace("\r", " ").replace("\n", " ").strip()
    if not safe_name:
        safe_name = "toan-aas-frame-video.mp4"
    return _SealedFrameVideoStreamingResponse(
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


def _expected_duration(operation: tuple[Any, ...]) -> float:
    return float(operation[7]) * int(operation[9])


def _completed_output_details(operation: tuple[Any, ...]) -> tuple[Path, int, str, int, int, float]:
    try:
        storage_key = str(operation[14] or "")
        byte_size = int(operation[17] or 0)
        digest = str(operation[18] or "")
        width = int(operation[12] or 0)
        height = int(operation[13] or 0)
        expected_duration = _expected_duration(operation)
    except (IndexError, TypeError, ValueError) as exc:
        raise FrameVideoError("Receipt Frame Video không hợp lệ", code="FRAME_VIDEO_OUTPUT_INVALID") from exc
    if (
        not storage_key
        or byte_size < 128
        or SHA256_PATTERN.fullmatch(digest) is None
        or width < 1
        or height < 1
        or expected_duration <= 0
        or expected_duration > MAX_OUTPUT_SECONDS
    ):
        raise FrameVideoError("Receipt Frame Video không hợp lệ", code="FRAME_VIDEO_OUTPUT_INVALID")
    return _output_path(_feature_root(), storage_key), byte_size, digest, width, height, expected_duration


@router.post("/estimate")
async def estimate_frame_video(payload: FrameVideoEstimateRequest, account: dict = Depends(require_account)):
    """Validate owner-selected image receipts and return a non-mutating plan."""

    _require_runtime()
    ensure_copyfast_schema()
    spec = _normalized_spec(payload)
    with transaction() as conn:
        sources = _sources_for_account(conn, source_asset_ids=list(payload.source_asset_ids), account_id=str(account["id"]))
    if sources is None:
        return _source_not_found()
    total_bytes = sum(int(source["byte_size"]) for source in sources)
    fingerprint = _request_fingerprint(source_snapshots=sources, spec=spec)
    return envelope(
        True,
        "Đã kiểm tra kế hoạch Frame Video; chưa tạo file và chưa ghi dữ liệu.",
        data={
            "estimate": {
                "source_count": len(sources),
                "source_total_bytes": total_bytes,
                "aspect_ratio": spec["aspect_ratio"],
                "width": spec["width"],
                "height": spec["height"],
                "seconds_per_image": spec["seconds_per_image"],
                "duration_seconds": spec["duration_seconds"],
                "effect": spec["effect"],
                "effective_effect": _effective_effect(str(spec["effect"]), fingerprint),
                "output": {"content_type": "video/mp4", "codec": "h264", "audio": False},
            }
        },
        status_name="draft",
    )


@router.get("")
async def list_frame_videos(
    limit: int = 20,
    offset: int = Query(0, ge=0, le=10_000),
    account: dict = Depends(require_account),
):
    _require_enabled()
    ensure_copyfast_schema()
    bounded_limit = max(1, min(int(limit), 50))
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT {OPERATION_SELECT} FROM web_frame_video_operations
                WHERE account_id=? ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (str(account["id"]), bounded_limit + 1, int(offset)),
        ).fetchall()
    operations = [tuple(row) for row in rows[:bounded_limit]]
    public = [_public_operation(operation) for operation in operations]
    return envelope(
        True,
        "Đã tải Frame Video riêng tư.",
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
async def create_frame_video(payload: FrameVideoRequest, request: Request, account: dict = Depends(require_csrf)):
    """Create one verified private MP4 from an immutable ordered image snapshot."""

    ffmpeg, ffprobe = _require_runtime()
    ensure_copyfast_schema()
    root = _feature_root()
    account_id = str(account["id"])
    spec = _normalized_spec(payload)
    operation_id = ""
    final_path: Path | None = None
    staging_paths: list[Path] = []
    image_capacity_reserved = False
    media_capacity_reserved = False
    sources: list[dict[str, Any]] = []
    active_source_id = ""
    try:
        with transaction() as conn:
            existing = conn.execute(
                f"""SELECT {OPERATION_SELECT} FROM web_frame_video_operations
                    WHERE account_id=? AND kind=? AND idempotency_key=?""",
                (account_id, FRAME_VIDEO_KIND, payload.idempotency_key),
            ).fetchone()
            if existing:
                operation = tuple(existing)
                stored_sources = _sources_for_operation(conn, str(operation[0]))
                if _replay_matches(operation, stored_sources, payload):
                    return _operation_response(operation, replay=True)
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho Frame Video khác")
            resolved_sources = _sources_for_account(
                conn,
                source_asset_ids=list(payload.source_asset_ids),
                account_id=account_id,
            )
            if resolved_sources is None:
                return _source_not_found()
            sources = resolved_sources

        if not image_decoder_capacity().acquire(blocking=False):
            raise HTTPException(status_code=429, detail="Frame Video đang bận chuẩn hoá ảnh khác; vui lòng thử lại sau ít phút")
        image_capacity_reserved = True
        if not media_ffmpeg_capacity().acquire(blocking=False):
            raise HTTPException(status_code=429, detail="Frame Video đang bận render một tác vụ media khác; vui lòng thử lại sau ít phút")
        media_capacity_reserved = True

        normalized_sources: list[Path] = []
        for source in sources:
            active_source_id = str(source["id"])
            raw_copy = _staging_path(root, f".source{str(source['extension'])}")
            normalized_copy = _staging_path(root, ".normalized.jpg")
            staging_paths.extend([raw_copy, normalized_copy])
            await run_in_threadpool(_copy_verified_image_source, raw_copy, source=source)
            await run_in_threadpool(
                _normalize_image_source,
                raw_copy,
                normalized_copy,
                extension=str(source["extension"]),
                target_width=int(spec["width"]),
                target_height=int(spec["height"]),
            )
            normalized_sources.append(normalized_copy)

        fingerprint = _request_fingerprint(source_snapshots=sources, spec=spec)
        effective_effect = _effective_effect(str(spec["effect"]), fingerprint)
        with transaction() as conn:
            existing = conn.execute(
                f"""SELECT {OPERATION_SELECT} FROM web_frame_video_operations
                    WHERE account_id=? AND kind=? AND idempotency_key=?""",
                (account_id, FRAME_VIDEO_KIND, payload.idempotency_key),
            ).fetchone()
            if existing:
                operation = tuple(existing)
                stored_sources = _sources_for_operation(conn, str(operation[0]))
                if _replay_matches(operation, stored_sources, payload):
                    return _operation_response(operation, replay=True)
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho Frame Video khác")
            current_sources = _sources_for_account(
                conn,
                source_asset_ids=list(payload.source_asset_ids),
                account_id=account_id,
            )
            if current_sources is None or current_sources != sources:
                return _source_not_found()
            now = utc_now()
            operation_id = str(uuid.uuid4())
            total_bytes = sum(int(source["byte_size"]) for source in sources)
            conn.execute(
                """INSERT INTO web_frame_video_operations
                   (id, account_id, kind, state, idempotency_key, request_fingerprint,
                    aspect_ratio, seconds_per_image, effect, source_count, source_total_bytes,
                    created_at, queued_at, updated_at)
                   VALUES (?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    operation_id,
                    account_id,
                    FRAME_VIDEO_KIND,
                    payload.idempotency_key,
                    fingerprint,
                    str(spec["aspect_ratio"]),
                    float(spec["seconds_per_image"]),
                    str(spec["effect"]),
                    len(sources),
                    total_bytes,
                    now,
                    now,
                    now,
                ),
            )
            for index, source in enumerate(sources):
                conn.execute(
                    """INSERT INTO web_frame_video_operation_sources
                       (id, operation_id, source_asset_id, source_index, source_sha256,
                        source_byte_size, source_extension, source_content_type, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid.uuid4()),
                        operation_id,
                        str(source["id"]),
                        index,
                        str(source["sha256"]),
                        int(source["byte_size"]),
                        str(source["extension"]),
                        str(source["content_type"]),
                        now,
                    ),
                )
            _record_event(conn, operation_id=operation_id, state="queued", when=now)
            conn.execute(
                """UPDATE web_frame_video_operations
                   SET state='processing', started_at=?, updated_at=?, revision=revision + 1
                   WHERE id=? AND account_id=? AND state='queued'""",
                (now, now, operation_id, account_id),
            )
            conn.execute(
                """INSERT INTO web_frame_video_operation_attempts
                   (id, operation_id, account_id, attempt_no, state, fence_token, started_at)
                   VALUES (?, ?, ?, 1, 'processing', ?, ?)""",
                (str(uuid.uuid4()), operation_id, account_id, str(uuid.uuid4()), now),
            )
            _record_event(conn, operation_id=operation_id, state="processing", when=now)

        rendered = _staging_path(root, ".rendered.mp4")
        staging_paths.append(rendered)
        await run_in_threadpool(
            _render_frame_video,
            ffmpeg,
            normalized_sources,
            rendered,
            width=int(spec["width"]),
            height=int(spec["height"]),
            seconds_per_image=float(spec["seconds_per_image"]),
            effective_effect=effective_effect,
        )
        output_bytes, output_digest, duration_ms = await run_in_threadpool(
            _verify_mp4_output,
            rendered,
            ffprobe=ffprobe,
            expected_width=int(spec["width"]),
            expected_height=int(spec["height"]),
            expected_duration_seconds=float(spec["duration_seconds"]),
        )
        final_path, storage_key = await run_in_threadpool(_publish_verified_output, root, rendered)
        # Verify again after the atomic publish; a completed database state is
        # never written from a staging-only check.
        output_bytes, output_digest, duration_ms = await run_in_threadpool(
            _verify_mp4_output,
            final_path,
            ffprobe=ffprobe,
            expected_width=int(spec["width"]),
            expected_height=int(spec["height"]),
            expected_duration_seconds=float(spec["duration_seconds"]),
            expected_bytes=output_bytes,
            expected_digest=output_digest,
        )
        now = utc_now()
        filename = f"toan-aas-frame-video-{operation_id}.mp4"
        with transaction() as conn:
            current = conn.execute(
                "SELECT state FROM web_frame_video_operations WHERE id=? AND account_id=?",
                (operation_id, account_id),
            ).fetchone()
            if not current or str(current[0]) != "processing":
                raise RuntimeError("Frame Video không còn ở trạng thái có thể hoàn tất")
            if not _quota_available(conn, account_id=account_id, additional_bytes=output_bytes):
                raise HTTPException(status_code=413, detail="Frame Video đã đạt quota lưu trữ của Web account")
            conn.execute(
                """UPDATE web_frame_video_operations
                   SET state='completed', output_duration_ms=?, output_width=?, output_height=?,
                       storage_key=?, original_filename=?, content_type='video/mp4', byte_size=?, sha256=?,
                       completed_at=?, updated_at=?, failure_code=NULL, revision=revision + 1
                   WHERE id=? AND account_id=? AND state='processing'""",
                (
                    duration_ms,
                    int(spec["width"]),
                    int(spec["height"]),
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
                """UPDATE web_frame_video_operation_attempts
                   SET state='completed', completed_at=?, failure_code=NULL
                   WHERE operation_id=? AND account_id=? AND state='processing'""",
                (now, operation_id, account_id),
            )
            _record_event(conn, operation_id=operation_id, state="completed", when=now)
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="web.frame_video.created",
                request_id=_request_id(request),
                target=operation_id,
                detail=(
                    f"sources={len(sources)};ratio={spec['aspect_ratio']};seconds={float(spec['seconds_per_image']):.3f};"
                    f"effect={effective_effect};duration_ms={duration_ms};bytes={output_bytes}"
                ),
            )
            completed = _operation_for_account(conn, operation_id, account_id)
        if completed is None:
            raise RuntimeError("Không thể đọc Frame Video vừa hoàn tất")
        final_path = None
        return _operation_response(completed)
    except FrameVideoError as exc:
        _safe_unlink(final_path)
        if exc.code == "FRAME_VIDEO_SOURCE_UNAVAILABLE" and active_source_id:
            # A descriptor-verified source failed after an active-row lookup.
            # Mark only the current owner-scoped source being copied; no
            # browser-controlled path enters this lifecycle transition.
            _mark_source_unavailable(active_source_id, account_id)
        _mark_failed(operation_id, account_id, request=request, code=exc.code)
        raise HTTPException(status_code=_error_status(exc.code), detail=exc.public_message) from exc
    except HTTPException as exc:
        _safe_unlink(final_path)
        _mark_failed(
            operation_id,
            account_id,
            request=request,
            code="FRAME_VIDEO_QUOTA" if exc.status_code == 413 else "FRAME_VIDEO_REQUEST",
        )
        raise
    except Exception as exc:
        _safe_unlink(final_path)
        _mark_failed(operation_id, account_id, request=request, code="FRAME_VIDEO_OPERATION")
        raise HTTPException(status_code=500, detail="Không thể tạo Frame Video an toàn") from exc
    finally:
        _safe_unlink_all(staging_paths)
        if media_capacity_reserved:
            media_ffmpeg_capacity().release()
        if image_capacity_reserved:
            image_decoder_capacity().release()


@router.get("/{operation_id}/download")
async def download_frame_video(operation_id: str, account: dict = Depends(require_account)):
    """Deliver a verified sealed MP4 only to the signed operation owner."""

    _require_runtime()
    operation_id = _uuid(operation_id, label="Mã Frame Video")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with transaction() as conn:
        operation = _operation_for_account(conn, operation_id, account_id)
    if operation is None or str(operation[3]) not in {"completed", "unavailable"}:
        return _operation_not_found()
    if str(operation[3]) != "completed":
        return _operation_unavailable()
    path: Path | None = None
    try:
        if str(operation[16] or "") != "video/mp4":
            raise FrameVideoError("Frame Video có MIME không hợp lệ", code="FRAME_VIDEO_OUTPUT_INVALID")
        path, byte_size, digest, width, height, expected_duration = _completed_output_details(operation)
        _, ffprobe = _runtime()
        await run_in_threadpool(
            _verify_mp4_output,
            path,
            ffprobe=ffprobe,
            expected_width=width,
            expected_height=height,
            expected_duration_seconds=expected_duration,
            expected_bytes=byte_size,
            expected_digest=digest,
        )
    except (FrameVideoError, OSError, RuntimeError):
        _mark_output_unavailable(operation_id, account_id)
        _safe_unlink(path)
        return _operation_unavailable()
    _reserve_download_capacity()
    try:
        sealed_stream = await run_in_threadpool(
            _prepare_sealed_output,
            path,
            expected_bytes=byte_size,
            expected_digest=digest,
        )
    except _SealedFrameVideoDeliveryError:
        _release_download_capacity()
        return envelope(
            False,
            "Không thể chuẩn bị Frame Video riêng tư để tải an toàn. Vui lòng thử lại.",
            status_name="guarded",
            error_code="FRAME_VIDEO_DELIVERY_UNAVAILABLE",
        )
    except Exception:
        _release_download_capacity()
        raise
    if sealed_stream is None:
        _release_download_capacity()
        _mark_output_unavailable(operation_id, account_id)
        _safe_unlink(path)
        return _operation_unavailable()
    finalizer = _sealed_download_finalizer(sealed_stream)
    try:
        return _attachment_response(
            sealed_stream,
            byte_size=byte_size,
            filename=str(operation[15] or "toan-aas-frame-video.mp4"),
            on_close=finalizer,
        )
    except Exception:
        finalizer()
        raise


@router.get("/{operation_id}")
async def get_frame_video(operation_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã Frame Video")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with transaction() as conn:
        operation = _operation_for_account(conn, operation_id, account_id)
        events = conn.execute(
            """SELECT state, created_at FROM web_frame_video_operation_events
               WHERE operation_id=? ORDER BY sequence ASC, id ASC LIMIT 60""",
            (operation_id,),
        ).fetchall()
    if operation is None:
        return _operation_not_found()
    public = _public_operation(operation)
    return envelope(
        True,
        "Đã tải trạng thái Frame Video riêng tư.",
        data={
            "operation": public,
            "events": [{"state": str(event[0]), "created_at": str(event[1])} for event in events],
        },
        status_name=str(public["state"]),
    )


def reconcile_frame_video_operation_storage(*, interrupted_before: str | None = None) -> None:
    """Fail closed for interrupted work, corrupt completed MP4s and old orphans."""

    if not frame_video_operations_enabled():
        return
    ensure_copyfast_schema()
    root = _feature_root()
    outputs = _private_directory(root, "outputs")
    staging = _private_directory(root, ".staging")
    _, ffprobe = _runtime()
    cutoff_fence = ""
    if interrupted_before:
        try:
            parsed = datetime.fromisoformat(str(interrupted_before).strip().replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("timezone")
            cutoff_fence = parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
        except ValueError as exc:
            raise RuntimeError("Startup Frame Video reconciliation fence không hợp lệ") from exc
    now = utc_now()
    with transaction() as conn:
        query = "SELECT id, account_id FROM web_frame_video_operations WHERE state IN ('queued', 'processing')"
        params: tuple[Any, ...] = ()
        if cutoff_fence:
            query += " AND COALESCE(started_at, queued_at, created_at, updated_at) < ?"
            params = (cutoff_fence,)
        interrupted = conn.execute(query, params).fetchall()
        for operation_id, account_id in interrupted:
            conn.execute(
                """UPDATE web_frame_video_operations
                   SET state='failed', failure_code='FRAME_VIDEO_INTERRUPTED', updated_at=?, revision=revision + 1
                   WHERE id=? AND state IN ('queued', 'processing')""",
                (now, str(operation_id)),
            )
            conn.execute(
                """UPDATE web_frame_video_operation_attempts
                   SET state='failed', completed_at=?, failure_code='FRAME_VIDEO_INTERRUPTED'
                   WHERE operation_id=? AND account_id=? AND state='processing'""",
                (now, str(operation_id), str(account_id)),
            )
            _record_event(conn, operation_id=str(operation_id), state="failed", when=now)
        completed_rows = conn.execute(
            f"SELECT {OPERATION_SELECT} FROM web_frame_video_operations WHERE state='completed'"
        ).fetchall()
    known_storage: set[str] = set()
    for row in completed_rows:
        operation = tuple(row)
        operation_id = str(operation[0])
        account_id = str(operation[1])
        path: Path | None = None
        valid = False
        try:
            path, byte_size, digest, width, height, expected_duration = _completed_output_details(operation)
            _verify_mp4_output(
                path,
                ffprobe=ffprobe,
                expected_width=width,
                expected_height=height,
                expected_duration_seconds=expected_duration,
                expected_bytes=byte_size,
                expected_digest=digest,
            )
            known_storage.add(str(operation[14]))
            valid = True
        except (FrameVideoError, OSError, RuntimeError):
            valid = False
        if not valid:
            _mark_output_unavailable(operation_id, account_id)
            _safe_unlink(path)
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
                modified = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc)
                if modified < cutoff:
                    candidate.unlink()
            except OSError:
                continue
