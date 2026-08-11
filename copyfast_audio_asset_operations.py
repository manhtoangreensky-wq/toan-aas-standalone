"""Bounded private Audio Asset Operations over an owner's Asset Vault files.

This is a deliberately narrow Web-native execution boundary.  It can inspect
one private audio file, convert it to a fixed MP3/M4A profile, or make one
fixed loudness-normalized M4A copy.  It is not an AI audio enhancer, a voice
clone/TTS/ASR/dubbing endpoint, a Bot/Core Bridge adapter, provider call, job,
wallet/Xu mutation, PayOS action, public URL or browser-owned FFmpeg surface.

The browser submits only an Asset Vault UUID, closed operation enum and
idempotency key.  Source bytes, local paths, process argv, codec selection,
hashes and output storage keys stay server-side.  A transformation is marked
completed only after a generated artifact is rehashed and re-probed both
before and after atomic publication to an isolated private root.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
from typing import Any, BinaryIO, Callable
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator
from starlette.concurrency import run_in_threadpool

from copyfast_assets import (
    open_verified_private_asset_stream,
    private_asset_attachment_response,
    seal_verified_private_file,
)
from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import (
    asset_vault_enabled,
    audio_asset_operations_directory,
    audio_asset_operation_export_enabled,
    audio_asset_operations_enabled,
    ensure_copyfast_schema,
    transaction,
    utc_now,
)
from copyfast_media_runtime import media_ffmpeg_capacity


router = APIRouter(prefix="/api/v1/audio-asset-operations", tags=["Web Audio Asset Operations"])

AUDIO_INSPECT_KIND = "audio_inspect"
AUDIO_CONVERT_KIND = "audio_convert"
AUDIO_NORMALIZE_KIND = "audio_normalize"
TRANSFORM_KINDS = frozenset({AUDIO_CONVERT_KIND, AUDIO_NORMALIZE_KIND})
SUPPORTED_KINDS = frozenset({AUDIO_INSPECT_KIND, *TRANSFORM_KINDS})
OPERATION_STATES = frozenset({"queued", "processing", "completed", "failed", "guarded", "unavailable"})
SOURCE_FORMATS = frozenset({"mp3", "wav", "m4a", "ogg"})
TARGET_FORMATS = frozenset({"mp3", "m4a"})
NORMALIZE_TARGET_FORMAT = "m4a"
NORMALIZE_PROFILE = "speech_safe_v1"

MIME_BY_FORMAT = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "ogg": "audio/ogg",
}
SOURCE_MIMES = {
    "mp3": frozenset({"audio/mpeg"}),
    "wav": frozenset({"audio/wav", "audio/x-wav"}),
    "m4a": frozenset({"audio/mp4"}),
    "ogg": frozenset({"audio/ogg", "application/ogg"}),
}
EXTENSION_BY_FORMAT = {"mp3": ".mp3", "wav": ".wav", "m4a": ".m4a", "ogg": ".ogg"}
OUTPUT_CODEC_BY_FORMAT = {"mp3": "mp3", "m4a": "aac"}
OUTPUT_FORMAT_NAMES = {"mp3": frozenset({"mp3"}), "m4a": frozenset({"mov", "mp4", "m4a"})}
OUTPUT_FILENAME_BY_FORMAT = {
    "mp3": "toan-aas-audio.mp3",
    "m4a": "toan-aas-audio.m4a",
}

UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
ASSET_STORAGE_KEY_PATTERN = re.compile(r"^objects/[0-9a-f]{32}\.blob$")
OUTPUT_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.(?P<suffix>mp3|m4a)$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

CHUNK_BYTES = 256 * 1024
MAX_INPUT_BYTES = 25 * 1024 * 1024
MAX_OUTPUT_BYTES = 12 * 1024 * 1024
MAX_DURATION_SECONDS = 600.0
MIN_DURATION_SECONDS = 0.25
MIN_SAMPLE_RATE = 8_000
MAX_SAMPLE_RATE = 48_000
MIN_CHANNELS = 1
MAX_CHANNELS = 2
PROBE_TIMEOUT_SECONDS = 6.0
RENDER_TIMEOUT_SECONDS = 45.0
OUTPUT_DURATION_TOLERANCE_SECONDS = 0.75
ORPHAN_RETENTION_SECONDS = 60 * 60
AUDIO_TOPOLOGY_SQLITE_SINGLE_REPLICA = "sqlite_single_replica"
REPLICA_COUNT_ENV_NAMES = ("RAILWAY_REPLICA_COUNT", "RAILWAY_REPLICAS", "WEBAPP_REPLICA_COUNT")

OPERATION_SELECT = """id, source_asset_id, project_id, kind, target_format, normalization_profile, state,
                      source_sha256, source_byte_size, source_lifecycle_revision, source_format,
                      source_duration_ms, source_channels, source_sample_rate, source_codec,
                      output_duration_ms, output_channels, output_sample_rate, output_codec,
                      storage_key, original_filename, content_type, byte_size, sha256, failure_code,
                      created_at, queued_at, started_at, completed_at, updated_at"""


class AudioAssetOperationError(Exception):
    """Known public-safe failure; never include process stderr or a local path."""

    def __init__(self, message: str, *, code: str = "AUDIO_OPERATION_INVALID"):
        super().__init__(message)
        self.public_message = message
        self.code = code


class AudioOperationAssetExportFailureDomain(str, Enum):
    """Classify source-opening failures without leaking private storage details."""

    PRECONDITION = "precondition"
    SOURCE_INTEGRITY = "source_integrity"
    RETRYABLE = "retryable"


@dataclass(frozen=True)
class AudioOperationAssetExportFailure:
    domain: AudioOperationAssetExportFailureDomain
    code: str
    public_message: str
    status_name: str = "guarded"

    @property
    def should_mark_output_unavailable(self) -> bool:
        return self.domain is AudioOperationAssetExportFailureDomain.SOURCE_INTEGRITY


@dataclass
class AudioOperationAssetExportPinnedSource:
    """A completed transform verified through the exact descriptor to copy."""

    stream: BinaryIO = field(repr=False)
    kind: str
    project_id: str | None
    target_format: str
    extension: str
    content_type: str
    byte_size: int
    digest: str = field(repr=False)
    duration_seconds: float
    duration_ms: int
    channels: int
    sample_rate: int
    codec: str
    format_name: str

    def close(self) -> None:
        self.stream.close()


@dataclass
class AudioOperationAssetExportSourceResult:
    source: AudioOperationAssetExportPinnedSource | None
    failure: AudioOperationAssetExportFailure | None
    _operation_id: str = field(repr=False)
    _account_id: str = field(repr=False)

    @property
    def is_source_integrity_failure(self) -> bool:
        return bool(self.failure and self.failure.should_mark_output_unavailable)

    def close(self) -> None:
        if self.source is not None:
            self.source.close()


class _BaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AudioAssetInspectRequest(_BaseRequest):
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


class AudioAssetConvertRequest(AudioAssetInspectRequest):
    target_format: StrictStr = Field(min_length=3, max_length=3)

    @field_validator("target_format")
    @classmethod
    def valid_target_format(cls, value: StrictStr) -> str:
        candidate = str(value or "").strip().lower()
        if candidate not in TARGET_FORMATS:
            raise ValueError("Định dạng đích chỉ nhận mp3 hoặc m4a")
        return candidate


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _safe_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed and parsed not in {float("inf"), float("-inf")} else None


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
    if not audio_asset_operations_enabled() or not asset_vault_enabled():
        raise HTTPException(
            status_code=503,
            detail="Audio Asset Operations cần Asset Vault private và storage đầu ra riêng đã được bật",
        )
    topology_code = _topology_guarded_code()
    if topology_code:
        raise HTTPException(
            status_code=503,
            detail="Audio Asset Operations chỉ chạy trên topology SQLite single-replica đã được xác nhận.",
        )


def _require_asset_export_enabled() -> None:
    """Fail closed before any account-scoped export lookup or source I/O."""

    if not asset_vault_enabled() or not audio_asset_operations_enabled() or not audio_asset_operation_export_enabled():
        raise HTTPException(
            status_code=503,
            detail="Lưu Audio Asset Operations vào Asset Vault chưa được bật",
        )


def _topology_guarded_code() -> str | None:
    topology = os.environ.get("WEBAPP_AUDIO_ASSET_OPERATIONS_TOPOLOGY", "").strip().lower()
    if topology != AUDIO_TOPOLOGY_SQLITE_SINGLE_REPLICA:
        return "AUDIO_TOPOLOGY_UNVERIFIED"
    attested = False
    for name in REPLICA_COUNT_ENV_NAMES:
        raw = os.environ.get(name, "").strip()
        if not raw:
            continue
        attested = True
        try:
            replicas = int(raw)
        except ValueError:
            return "AUDIO_REPLICA_COUNT_UNVERIFIED"
        if replicas != 1:
            return "AUDIO_MULTI_REPLICA_BLOCKED"
    return None if attested else "AUDIO_REPLICA_COUNT_UNVERIFIED"


def _binary_path(*environment_names: str, expected_name: str) -> str:
    configured = ""
    for name in environment_names:
        configured = os.environ.get(name, "").strip()
        if configured:
            break
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            raise AudioAssetOperationError("Runtime Audio Asset Operations chưa có binary tuyệt đối đã kiểm định", code="AUDIO_RUNTIME_UNAVAILABLE")
    else:
        discovered = shutil.which(expected_name)
        if not discovered:
            raise AudioAssetOperationError("Runtime Audio Asset Operations chưa có FFmpeg/ffprobe", code="AUDIO_RUNTIME_UNAVAILABLE")
        candidate = Path(discovered)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise AudioAssetOperationError("Runtime Audio Asset Operations chưa có binary hợp lệ", code="AUDIO_RUNTIME_UNAVAILABLE") from exc
    acceptable = {expected_name.lower(), f"{expected_name}.exe".lower()}
    if resolved.name.lower() not in acceptable or not resolved.is_file():
        raise AudioAssetOperationError("Runtime Audio Asset Operations chưa có binary hợp lệ", code="AUDIO_RUNTIME_UNAVAILABLE")
    if os.name != "nt" and not os.access(resolved, os.X_OK):
        raise AudioAssetOperationError("Runtime Audio Asset Operations chưa có binary có thể chạy", code="AUDIO_RUNTIME_UNAVAILABLE")
    return str(resolved)


def _audio_runtime() -> tuple[str, str]:
    return (
        _binary_path("WEBAPP_AUDIO_ASSET_OPERATIONS_FFMPEG_BIN", "WEBAPP_VIDEO_FFMPEG_BIN", expected_name="ffmpeg"),
        _binary_path("WEBAPP_AUDIO_ASSET_OPERATIONS_FFPROBE_BIN", "WEBAPP_VIDEO_FFPROBE_BIN", expected_name="ffprobe"),
    )


def _require_runtime() -> tuple[str, str]:
    _require_enabled()
    try:
        return _audio_runtime()
    except AudioAssetOperationError as exc:
        raise HTTPException(status_code=503, detail=exc.public_message) from exc


def ensure_audio_asset_operations_runtime() -> None:
    """Fail closed only after this optional local processor is enabled."""

    if not audio_asset_operations_enabled():
        return
    if not asset_vault_enabled():
        raise RuntimeError("Audio Asset Operations cần WEBAPP_ASSET_VAULT_ENABLED=true")
    if _topology_guarded_code():
        raise RuntimeError("Audio Asset Operations cần topology SQLite single-replica đã được xác nhận")
    _audio_runtime()


def _maximum_account_bytes() -> int:
    raw = os.environ.get("WEBAPP_AUDIO_ASSET_OPERATIONS_QUOTA_MB", "64").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 64
    return max(12, min(value, 512)) * 1024 * 1024


def _private_directory(root: Path, name: str) -> Path:
    if name not in {".staging", "outputs"}:
        raise RuntimeError("Thư mục Audio Asset Operations không hợp lệ")
    private_root = root.resolve()
    candidate = private_root / name
    if candidate.exists() and candidate.is_symlink():
        raise RuntimeError("Thư mục Audio Asset Operations không được là symbolic link")
    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise RuntimeError("Thư mục Audio Asset Operations không hợp lệ")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError("Thư mục Audio Asset Operations vượt ngoài storage riêng") from exc
    return resolved


def _staging_path(root: Path, suffix: str) -> Path:
    return _private_directory(root, ".staging") / f"{uuid.uuid4().hex}{suffix}"


def _output_path(root: Path, storage_key: str, *, expected_format: str | None = None) -> Path:
    match = OUTPUT_STORAGE_KEY_PATTERN.fullmatch(str(storage_key or ""))
    if not match or (expected_format is not None and match.group("suffix") != expected_format):
        raise RuntimeError("Storage key Audio Asset Operations không hợp lệ")
    private_root = root.resolve()
    candidate = private_root / storage_key
    try:
        candidate.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError("Storage key Audio Asset Operations vượt ngoài storage riêng") from exc
    return candidate


def _safe_unlink(path: Path | None) -> None:
    if path is None:
        return
    try:
        if path.is_file() and not path.is_symlink():
            path.unlink()
    except OSError:
        pass


def _safe_unlink_private_output(path: Path | None) -> None:
    if path is None:
        return
    try:
        parent = os.lstat(path.parent)
        leaf = os.lstat(path)
        if not stat.S_ISDIR(parent.st_mode) or stat.S_ISLNK(parent.st_mode):
            return
        if not (stat.S_ISREG(leaf.st_mode) or stat.S_ISLNK(leaf.st_mode)):
            return
        path.unlink()
    except OSError:
        pass


def _publish_output(staged: Path, final_path: Path) -> None:
    if not staged.is_file() or staged.is_symlink():
        raise AudioAssetOperationError("Output audio không còn sẵn sàng", code="AUDIO_OUTPUT_INVALID")
    try:
        parent = os.lstat(final_path.parent)
        if not stat.S_ISDIR(parent.st_mode) or stat.S_ISLNK(parent.st_mode):
            raise AudioAssetOperationError("Không thể khóa storage audio riêng tư", code="AUDIO_OUTPUT_INVALID")
        if final_path.exists() or final_path.is_symlink():
            raise AudioAssetOperationError("Không thể chuẩn bị output audio riêng tư", code="AUDIO_OUTPUT_INVALID")
        os.replace(staged, final_path)
    except AudioAssetOperationError:
        raise
    except OSError as exc:
        raise AudioAssetOperationError("Không thể chuẩn bị output audio riêng tư", code="AUDIO_OUTPUT_INVALID") from exc


def _source_format(extension: Any, content_type: Any) -> str | None:
    suffix = str(extension or "").strip().lower()
    media_type = str(content_type or "").strip().lower()
    for fmt in SOURCE_FORMATS:
        if suffix == EXTENSION_BY_FORMAT[fmt] and media_type in SOURCE_MIMES[fmt]:
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


def _request_fingerprint(
    *,
    kind: str,
    source: dict[str, Any],
    target_format: str | None,
    normalization_profile: str | None,
) -> str:
    payload = json.dumps(
        {
            "kind": kind,
            "source_asset_id": str(source["asset_id"]),
            "source_sha256": str(source["sha256"]),
            "source_byte_size": int(source["byte_size"]),
            "source_lifecycle_revision": int(source["lifecycle_revision"]),
            "source_format": str(source["format"]),
            "target_format": target_format or "",
            "normalization_profile": normalization_profile or "",
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _record_event(conn: Any, *, operation_id: str, state: str, when: str | None = None) -> None:
    if state not in OPERATION_STATES:
        raise RuntimeError("Trạng thái Audio Asset Operation không hợp lệ")
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 FROM web_audio_asset_operation_events WHERE operation_id=?",
        (operation_id,),
    ).fetchone()
    sequence = int(row[0] or 1) if row else 1
    conn.execute(
        """INSERT INTO web_audio_asset_operation_events (id, operation_id, state, sequence, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), operation_id, state, sequence, when or utc_now()),
    )


def _operation_row(conn: Any, *, operation_id: str, account_id: str):
    return conn.execute(
        f"SELECT {OPERATION_SELECT} FROM web_audio_asset_operations WHERE id=? AND account_id=?",
        (operation_id, account_id),
    ).fetchone()


def _operation_public(row: tuple[Any, ...]) -> dict[str, Any]:
    (
        operation_id, _source_asset_id, _project_id, kind, target_format, normalization_profile, state,
        _source_sha256, _source_byte_size, _source_lifecycle_revision, source_format,
        source_duration_ms, source_channels, source_sample_rate, source_codec,
        output_duration_ms, output_channels, output_sample_rate, output_codec,
        storage_key, _original_filename, content_type, byte_size, sha256, _failure_code,
        created_at, queued_at, started_at, completed_at, updated_at,
    ) = row
    normalized_kind = str(kind or "")
    normalized_target = str(target_format or "")
    completed = str(state or "") == "completed"
    canonical_output = (
        normalized_kind in TRANSFORM_KINDS
        and normalized_target in TARGET_FORMATS
        and completed
        and OUTPUT_STORAGE_KEY_PATTERN.fullmatch(str(storage_key or "")) is not None
        and str(storage_key or "").endswith(EXTENSION_BY_FORMAT[normalized_target])
        and str(content_type or "") == MIME_BY_FORMAT[normalized_target]
        and isinstance(byte_size, int)
        and 0 < byte_size <= MAX_OUTPUT_BYTES
        and SHA256_PATTERN.fullmatch(str(sha256 or "").lower()) is not None
        and str(output_codec or "") == OUTPUT_CODEC_BY_FORMAT[normalized_target]
        and _safe_int(output_duration_ms) is not None
        and _safe_int(output_channels) in {1, 2}
        and _safe_int(output_sample_rate) == 48_000
    )
    return {
        "id": str(operation_id),
        "kind": normalized_kind,
        "state": str(state or "guarded"),
        "status": str(state or "guarded"),
        "source_format": str(source_format or "") if str(source_format or "") in SOURCE_FORMATS else None,
        "target_format": normalized_target if normalized_target in TARGET_FORMATS else None,
        "normalization_profile": (
            str(normalization_profile) if normalized_kind == AUDIO_NORMALIZE_KIND and str(normalization_profile) == NORMALIZE_PROFILE else None
        ),
        "source_duration_ms": _safe_int(source_duration_ms),
        "source_channels": _safe_int(source_channels),
        "source_sample_rate": _safe_int(source_sample_rate),
        "source_codec": str(source_codec or "")[:48] or None,
        "output_duration_ms": _safe_int(output_duration_ms) if canonical_output else None,
        "output_channels": _safe_int(output_channels) if canonical_output else None,
        "output_sample_rate": _safe_int(output_sample_rate) if canonical_output else None,
        "output_codec": str(output_codec or "")[:48] if canonical_output else None,
        "output_available": canonical_output,
        "filename": OUTPUT_FILENAME_BY_FORMAT[normalized_target] if canonical_output else None,
        "content_type": MIME_BY_FORMAT[normalized_target] if canonical_output else None,
        "byte_size": int(byte_size) if canonical_output else None,
        "created_at": str(created_at or ""),
        "queued_at": str(queued_at or ""),
        "started_at": str(started_at) if started_at else None,
        "completed_at": str(completed_at) if completed_at else None,
        "updated_at": str(updated_at or ""),
    }


def _format_name_matches(target_format: str, format_name: str) -> bool:
    names = {item.strip().lower() for item in str(format_name or "").split(",") if item.strip()}
    return bool(names & OUTPUT_FORMAT_NAMES.get(target_format, frozenset()))


def _audio_magic_matches(fmt: str, prefix: bytes) -> bool:
    if fmt == "mp3":
        return prefix.startswith(b"ID3") or (len(prefix) >= 2 and prefix[0] == 0xFF and (prefix[1] & 0xE0) == 0xE0)
    if fmt == "wav":
        return len(prefix) >= 12 and prefix[:4] == b"RIFF" and prefix[8:12] == b"WAVE"
    if fmt == "m4a":
        return len(prefix) >= 12 and prefix[4:8] == b"ftyp"
    if fmt == "ogg":
        return prefix.startswith(b"OggS")
    return False


def _probe_audio(
    ffprobe: str,
    source: Path | str,
    *,
    input_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Probe one local file or server-owned byte stream with fixed argv only."""

    command = [
        ffprobe,
        "-v", "error",
        "-protocol_whitelist", "file,pipe",
        "-show_entries", "format=format_name,duration:stream=codec_type,codec_name,channels,sample_rate,duration",
        "-of", "json",
        str(source),
    ]
    run_options: dict[str, Any] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.DEVNULL,
        "timeout": PROBE_TIMEOUT_SECONDS,
        "shell": False,
        "check": False,
    }
    if input_bytes is None:
        run_options["stdin"] = subprocess.DEVNULL
    else:
        if not isinstance(input_bytes, bytes) or len(input_bytes) > MAX_OUTPUT_BYTES:
            raise AudioAssetOperationError("Audio vượt giới hạn Audio Asset Operations", code="AUDIO_PROBE_LIMIT")
        run_options["input"] = input_bytes
    try:
        completed = subprocess.run(
            command,
            **run_options,
        )
    except subprocess.TimeoutExpired as exc:
        raise AudioAssetOperationError("Kiểm tra audio vượt thời gian an toàn", code="AUDIO_PROBE_TIMEOUT") from exc
    except OSError as exc:
        raise AudioAssetOperationError("Không thể khởi động runtime Audio Asset Operations", code="AUDIO_RUNTIME_UNAVAILABLE") from exc
    if completed.returncode != 0 or len(completed.stdout) > 16 * 1024:
        raise AudioAssetOperationError("Audio không vượt qua kiểm tra định dạng", code="AUDIO_PROBE_INVALID")
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AudioAssetOperationError("Audio không vượt qua kiểm tra định dạng", code="AUDIO_PROBE_INVALID") from exc
    streams = payload.get("streams") if isinstance(payload, dict) else None
    if not isinstance(streams, list) or len(streams) != 1 or not isinstance(streams[0], dict):
        raise AudioAssetOperationError("Audio phải có đúng một audio stream an toàn", code="AUDIO_PROBE_LIMIT")
    stream = streams[0]
    if str(stream.get("codec_type") or "") != "audio":
        raise AudioAssetOperationError("Audio phải có đúng một audio stream an toàn", code="AUDIO_PROBE_LIMIT")
    fmt = payload.get("format") if isinstance(payload, dict) and isinstance(payload.get("format"), dict) else {}
    duration = _safe_float(fmt.get("duration")) or _safe_float(stream.get("duration"))
    channels = _safe_int(stream.get("channels"))
    sample_rate = _safe_int(stream.get("sample_rate"))
    codec = str(stream.get("codec_name") or "").strip().lower()
    format_name = str(fmt.get("format_name") or "").strip().lower()
    if (
        duration is None
        or duration < MIN_DURATION_SECONDS
        or duration > MAX_DURATION_SECONDS
        or channels is None
        or channels < MIN_CHANNELS
        or channels > MAX_CHANNELS
        or sample_rate is None
        or sample_rate < MIN_SAMPLE_RATE
        or sample_rate > MAX_SAMPLE_RATE
        or not codec
        or not format_name
    ):
        raise AudioAssetOperationError("Audio vượt giới hạn Audio Asset Operations", code="AUDIO_PROBE_LIMIT")
    return {
        "duration_seconds": duration,
        "duration_ms": int(round(duration * 1000)),
        "channels": channels,
        "sample_rate": sample_rate,
        "codec": codec[:48],
        "format_name": format_name[:160],
    }


def _probe_pinned_audio_export_stream(ffprobe: str, stream: BinaryIO) -> dict[str, Any]:
    """Probe exactly the server-pinned export bytes, never their pathname."""

    try:
        stream.seek(0)
        payload = stream.read(MAX_OUTPUT_BYTES + 1)
        stream.seek(0)
    except (OSError, ValueError) as exc:
        raise AudioAssetOperationError("Output audio không còn integrity", code="AUDIO_OUTPUT_INVALID") from exc
    if not isinstance(payload, bytes) or len(payload) > MAX_OUTPUT_BYTES:
        raise AudioAssetOperationError("Output audio vượt giới hạn lưu trữ", code="AUDIO_OUTPUT_LIMIT")
    return _probe_audio(ffprobe, "pipe:0", input_bytes=payload)


def _copy_verified_source(source: dict[str, Any], destination: Path) -> None:
    stream = open_verified_private_asset_stream(
        storage_key=str(source["storage_key"]),
        expected_bytes=int(source["byte_size"]),
        expected_digest=str(source["sha256"]),
    )
    if stream is None:
        raise AudioAssetOperationError("Audio nguồn không còn integrity để xử lý", code="AUDIO_SOURCE_UNAVAILABLE")
    digest = hashlib.sha256()
    total = 0
    prefix = bytearray()
    try:
        with stream, destination.open("xb") as output:
            while True:
                chunk = stream.read(CHUNK_BYTES)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_INPUT_BYTES:
                    raise AudioAssetOperationError("Tệp audio vượt giới hạn an toàn", code="AUDIO_INPUT_TOO_LARGE")
                if len(prefix) < 64:
                    prefix.extend(chunk[: 64 - len(prefix)])
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
    except AudioAssetOperationError:
        _safe_unlink(destination)
        raise
    except OSError as exc:
        _safe_unlink(destination)
        raise AudioAssetOperationError("Không thể chuẩn bị audio nguồn riêng tư", code="AUDIO_SOURCE_UNAVAILABLE") from exc
    if (
        total != int(source["byte_size"])
        or not hmac.compare_digest(digest.hexdigest(), str(source["sha256"]))
        or not _audio_magic_matches(str(source["format"]), bytes(prefix))
    ):
        _safe_unlink(destination)
        raise AudioAssetOperationError("Audio nguồn không vượt qua kiểm tra integrity", code="AUDIO_SOURCE_UNAVAILABLE")


def _render_audio(
    ffmpeg: str,
    source: Path,
    destination: Path,
    *,
    target_format: str,
    normalize: bool,
) -> None:
    if target_format not in TARGET_FORMATS:
        raise AudioAssetOperationError("Định dạng output audio không hợp lệ", code="AUDIO_TARGET_UNSUPPORTED")
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
        "-map", "0:a:0",
        "-vn",
        "-sn",
        "-dn",
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-ar", "48000",
        "-ac", "2",
    ]
    if normalize:
        # Fixed one-pass local profile. It is not browser-provided, not an
        # external loudness certification and does not imply enhancement/AI.
        command.extend(["-af", "loudnorm=I=-16:LRA=11:TP=-1.5"])
    if target_format == "mp3":
        command.extend(["-c:a", "libmp3lame", "-b:a", "128k", "-f", "mp3"])
    else:
        command.extend(["-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-f", "mp4"])
    command.extend(["-fs", str(MAX_OUTPUT_BYTES), "-n", str(destination)])
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
        raise AudioAssetOperationError("Xử lý audio vượt thời gian an toàn", code="AUDIO_RENDER_TIMEOUT") from exc
    except OSError as exc:
        raise AudioAssetOperationError("Không thể khởi động runtime Audio Asset Operations", code="AUDIO_RUNTIME_UNAVAILABLE") from exc
    if completed.returncode != 0:
        raise AudioAssetOperationError("Không thể xử lý audio từ tệp này", code="AUDIO_RENDER_FAILED")


def _digest_path(path: Path, *, maximum_bytes: int) -> tuple[int, str]:
    try:
        if not path.is_file() or path.is_symlink():
            raise AudioAssetOperationError("Output audio không còn sẵn sàng", code="AUDIO_OUTPUT_INVALID")
        size = int(path.stat().st_size)
        if size < 1 or size > maximum_bytes:
            raise AudioAssetOperationError("Output audio vượt giới hạn lưu trữ", code="AUDIO_OUTPUT_LIMIT")
        digest = hashlib.sha256()
        read = 0
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(CHUNK_BYTES)
                if not chunk:
                    break
                read += len(chunk)
                if read > maximum_bytes:
                    raise AudioAssetOperationError("Output audio vượt giới hạn lưu trữ", code="AUDIO_OUTPUT_LIMIT")
                digest.update(chunk)
        if read != size:
            raise AudioAssetOperationError("Output audio không còn sẵn sàng", code="AUDIO_OUTPUT_INVALID")
        return size, digest.hexdigest()
    except AudioAssetOperationError:
        raise
    except OSError as exc:
        raise AudioAssetOperationError("Output audio không hợp lệ", code="AUDIO_OUTPUT_INVALID") from exc


def _verify_output_path(
    path: Path,
    *,
    target_format: str,
    expected_bytes: int | None = None,
    expected_digest: str | None = None,
    expected_duration_seconds: float | None = None,
) -> tuple[int, str, dict[str, Any]]:
    if target_format not in TARGET_FORMATS:
        raise AudioAssetOperationError("Output audio không hợp lệ", code="AUDIO_OUTPUT_INVALID")
    byte_size, digest = _digest_path(path, maximum_bytes=MAX_OUTPUT_BYTES)
    if expected_bytes is not None and byte_size != expected_bytes:
        raise AudioAssetOperationError("Output audio không vượt qua kiểm tra integrity", code="AUDIO_OUTPUT_INVALID")
    if expected_digest is not None and not hmac.compare_digest(digest, expected_digest):
        raise AudioAssetOperationError("Output audio không vượt qua kiểm tra integrity", code="AUDIO_OUTPUT_INVALID")
    _ffmpeg, ffprobe = _audio_runtime()
    metadata = _probe_audio(ffprobe, path)
    if (
        not _format_name_matches(target_format, str(metadata["format_name"]))
        or str(metadata["codec"]) != OUTPUT_CODEC_BY_FORMAT[target_format]
        or int(metadata["channels"]) not in {1, 2}
        or int(metadata["sample_rate"]) != 48_000
    ):
        raise AudioAssetOperationError("Output audio không vượt qua kiểm tra định dạng", code="AUDIO_OUTPUT_INVALID")
    if expected_duration_seconds is not None and abs(float(metadata["duration_seconds"]) - expected_duration_seconds) > OUTPUT_DURATION_TOLERANCE_SECONDS:
        raise AudioAssetOperationError("Output audio không vượt qua kiểm tra thời lượng", code="AUDIO_OUTPUT_INVALID")
    return byte_size, digest, metadata


def _publish_verified_output(
    root: Path,
    staged: Path,
    *,
    target_format: str,
    expected_duration_seconds: float,
) -> tuple[Path, str, int, str, dict[str, Any]]:
    final_path: Path | None = None
    try:
        output_bytes, output_digest, metadata = _verify_output_path(
            staged,
            target_format=target_format,
            expected_duration_seconds=expected_duration_seconds,
        )
        _private_directory(root, "outputs")
        storage_key = f"outputs/{uuid.uuid4().hex}.{target_format}"
        final_path = _output_path(root, storage_key, expected_format=target_format)
        _publish_output(staged, final_path)
        verified_bytes, verified_digest, verified_metadata = _verify_output_path(
            final_path,
            target_format=target_format,
            expected_bytes=output_bytes,
            expected_digest=output_digest,
            expected_duration_seconds=expected_duration_seconds,
        )
        if verified_bytes != output_bytes or not hmac.compare_digest(verified_digest, output_digest) or verified_metadata != metadata:
            raise AudioAssetOperationError("Output audio không vượt qua kiểm tra integrity", code="AUDIO_OUTPUT_INVALID")
        accepted = final_path
        final_path = None
        return accepted, storage_key, output_bytes, output_digest, metadata
    except Exception:
        _safe_unlink_private_output(final_path)
        raise


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
             FROM web_audio_asset_operations
            WHERE account_id=? AND kind IN (?, ?) AND state='completed' AND byte_size IS NOT NULL""",
        (account_id, AUDIO_CONVERT_KIND, AUDIO_NORMALIZE_KIND),
    ).fetchone()
    used = int(row[0] or 0) if row else 0
    return used + additional_bytes <= _maximum_account_bytes()


def _mark_terminal(operation_id: str, account_id: str, *, code: str, request_id: str, state: str = "failed") -> None:
    normalized_state = state if state in {"failed", "guarded"} else "failed"
    now = utc_now()
    with transaction() as conn:
        current = conn.execute(
            "SELECT state FROM web_audio_asset_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
        if not current or str(current[0]) not in {"queued", "processing"}:
            return
        changed = conn.execute(
            """UPDATE web_audio_asset_operations
                   SET state=?, failure_code=?, updated_at=?
                 WHERE id=? AND account_id=? AND state IN ('queued', 'processing')""",
            (normalized_state, code[:80], now, operation_id, account_id),
        ).rowcount
        if changed == 1:
            _record_event(conn, operation_id=operation_id, state=normalized_state, when=now)
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="web.audio_asset_operation.failed",
                request_id=request_id,
                target=operation_id,
                detail=f"code={code[:80]}",
            )


def _terminal_source_changed_in_transaction(
    conn: Any,
    *,
    operation_id: str,
    account_id: str,
    now: str,
    request_id: str,
) -> None:
    """Fail a claimed operation closed without opening a nested SQLite write.

    A source can be archived, replaced or have its lifecycle revision changed
    between the private copy/probe and final write.  This helper deliberately
    runs in the caller's transaction: opening ``transaction()`` again here
    would contend with its own ``BEGIN IMMEDIATE`` and could leave a truthful
    failure stuck in ``processing``.
    """

    changed = conn.execute(
        """UPDATE web_audio_asset_operations
               SET state='failed', failure_code='AUDIO_SOURCE_CHANGED', updated_at=?
             WHERE id=? AND account_id=? AND state IN ('queued', 'processing')""",
        (now, operation_id, account_id),
    ).rowcount
    if changed == 1:
        _record_event(conn, operation_id=operation_id, state="failed", when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.audio_asset_operation.failed",
            request_id=request_id,
            target=operation_id,
            detail="code=AUDIO_SOURCE_CHANGED",
        )


def _mark_output_unavailable(operation_id: str, account_id: str, *, request_id: str = "system:audio_asset_storage") -> None:
    now = utc_now()
    with transaction() as conn:
        changed = conn.execute(
            """UPDATE web_audio_asset_operations
                   SET state='unavailable', failure_code='AUDIO_OUTPUT_UNAVAILABLE', updated_at=?
                 WHERE id=? AND account_id=? AND state='completed' AND kind IN (?, ?)""",
            (now, operation_id, account_id, AUDIO_CONVERT_KIND, AUDIO_NORMALIZE_KIND),
        ).rowcount
        if changed == 1:
            _record_event(conn, operation_id=operation_id, state="unavailable", when=now)
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="web.audio_asset_operation.unavailable",
                request_id=request_id,
                target=operation_id,
                detail="code=AUDIO_OUTPUT_UNAVAILABLE",
            )


def _claim_operation(operation_id: str, account_id: str, *, request_id: str) -> tuple[dict[str, Any], str, str | None, str | None] | None:
    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            """SELECT o.source_asset_id, o.source_sha256, o.source_byte_size, o.source_lifecycle_revision,
                      o.source_format, o.kind, o.target_format, o.normalization_profile,
                      f.project_id, f.extension, f.content_type, f.byte_size, f.sha256, f.storage_key, f.lifecycle_revision
                 FROM web_audio_asset_operations o
                 JOIN web_asset_files f ON f.id=o.source_asset_id AND f.account_id=o.account_id
                WHERE o.id=? AND o.account_id=? AND o.state='queued' AND f.state='active'""",
            (operation_id, account_id),
        ).fetchone()
        if not row:
            queued = conn.execute(
                "SELECT state FROM web_audio_asset_operations WHERE id=? AND account_id=?",
                (operation_id, account_id),
            ).fetchone()
            if queued and str(queued[0]) == "queued":
                changed = conn.execute(
                    """UPDATE web_audio_asset_operations
                           SET state='failed', failure_code='AUDIO_SOURCE_UNAVAILABLE', updated_at=?
                         WHERE id=? AND account_id=? AND state='queued'""",
                    (now, operation_id, account_id),
                ).rowcount
                if changed == 1:
                    _record_event(conn, operation_id=operation_id, state="failed", when=now)
            return None
        (
            source_asset_id, snapshot_digest, snapshot_bytes, snapshot_revision, snapshot_format,
            kind, target_format, normalization_profile, project_id, extension, content_type,
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
        valid = (
            actual_format in SOURCE_FORMATS
            and str(snapshot_format) == actual_format
            and str(snapshot_digest) == source["sha256"]
            and _safe_int(snapshot_bytes) == source["byte_size"]
            and _safe_int(snapshot_revision) == source["lifecycle_revision"]
            and source["byte_size"] is not None
            and source["lifecycle_revision"] is not None
            and 0 < int(source["byte_size"]) <= MAX_INPUT_BYTES
            and int(source["lifecycle_revision"]) >= 1
            and SHA256_PATTERN.fullmatch(str(source["sha256"])) is not None
            and ASSET_STORAGE_KEY_PATTERN.fullmatch(str(source["storage_key"])) is not None
        )
        if not valid:
            changed = conn.execute(
                """UPDATE web_audio_asset_operations
                       SET state='failed', failure_code='AUDIO_SOURCE_CHANGED', updated_at=?
                     WHERE id=? AND account_id=? AND state='queued'""",
                (now, operation_id, account_id),
            ).rowcount
            if changed == 1:
                _record_event(conn, operation_id=operation_id, state="failed", when=now)
            return None
        changed = conn.execute(
            """UPDATE web_audio_asset_operations
                   SET state='processing', started_at=?, updated_at=?
                 WHERE id=? AND account_id=? AND state='queued'""",
            (now, now, operation_id, account_id),
        ).rowcount
        if changed != 1:
            return None
        _record_event(conn, operation_id=operation_id, state="processing", when=now)
        return source, str(kind), str(target_format) if target_format else None, str(normalization_profile) if normalization_profile else None


def _complete_inspect(
    *,
    operation_id: str,
    account_id: str,
    source: dict[str, Any],
    metadata: dict[str, Any],
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
            """UPDATE web_audio_asset_operations
                   SET state='completed', source_duration_ms=?, source_channels=?, source_sample_rate=?,
                       source_codec=?, completed_at=?, updated_at=?, failure_code=NULL
                 WHERE id=? AND account_id=? AND state='processing'""",
            (
                int(metadata["duration_ms"]), int(metadata["channels"]), int(metadata["sample_rate"]),
                str(metadata["codec"]), now, now, operation_id, account_id,
            ),
        ).rowcount
        if changed != 1:
            return False
        _record_event(conn, operation_id=operation_id, state="completed", when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.audio_asset_operation.inspected",
            request_id=request_id,
            target=operation_id,
            detail=f"format={source['format']};duration_ms={int(metadata['duration_ms'])}",
        )
        return True


def _complete_transform(
    *,
    operation_id: str,
    account_id: str,
    source: dict[str, Any],
    source_metadata: dict[str, Any],
    target_format: str,
    storage_key: str,
    output_bytes: int,
    output_digest: str,
    output_metadata: dict[str, Any],
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
        if not _quota_available(conn, account_id=account_id, additional_bytes=output_bytes):
            raise AudioAssetOperationError("Audio Asset Operations đã đạt quota của Web account", code="AUDIO_OUTPUT_QUOTA")
        changed = conn.execute(
            """UPDATE web_audio_asset_operations
                   SET state='completed', source_duration_ms=?, source_channels=?, source_sample_rate=?, source_codec=?,
                       output_duration_ms=?, output_channels=?, output_sample_rate=?, output_codec=?,
                       storage_key=?, original_filename=?, content_type=?, byte_size=?, sha256=?,
                       completed_at=?, updated_at=?, failure_code=NULL
                 WHERE id=? AND account_id=? AND state='processing'""",
            (
                int(source_metadata["duration_ms"]), int(source_metadata["channels"]), int(source_metadata["sample_rate"]),
                str(source_metadata["codec"]), int(output_metadata["duration_ms"]), int(output_metadata["channels"]),
                int(output_metadata["sample_rate"]), str(output_metadata["codec"]), storage_key,
                OUTPUT_FILENAME_BY_FORMAT[target_format], MIME_BY_FORMAT[target_format], output_bytes, output_digest,
                now, now, operation_id, account_id,
            ),
        ).rowcount
        if changed != 1:
            return False
        _record_event(conn, operation_id=operation_id, state="completed", when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.audio_asset_operation.transformed",
            request_id=request_id,
            target=operation_id,
            detail=f"target={target_format};duration_ms={int(output_metadata['duration_ms'])};bytes={output_bytes}",
        )
        return True


def _operation_public_with_verified_output(row: tuple[Any, ...]) -> dict[str, Any]:
    operation = _operation_public(row)
    if not operation["output_available"]:
        return operation
    if verified_audio_asset_output_available(
        target_format=row[4],
        storage_key=row[19],
        content_type=row[21],
        byte_size=row[22],
        digest=row[23],
        output_duration_ms=row[15],
        output_channels=row[16],
        output_sample_rate=row[17],
        output_codec=row[18],
    ):
        return operation
    operation["output_available"] = False
    operation["filename"] = None
    operation["content_type"] = None
    operation["byte_size"] = None
    operation["output_duration_ms"] = None
    operation["output_channels"] = None
    operation["output_sample_rate"] = None
    operation["output_codec"] = None
    return operation


def verified_audio_asset_output_available(
    *,
    target_format: Any,
    storage_key: Any,
    content_type: Any,
    byte_size: Any,
    digest: Any,
    output_duration_ms: Any,
    output_channels: Any,
    output_sample_rate: Any,
    output_codec: Any,
) -> bool:
    target = str(target_format or "")
    expected_bytes = _safe_int(byte_size)
    expected_duration = _safe_int(output_duration_ms)
    if (
        target not in TARGET_FORMATS
        or str(content_type or "") != MIME_BY_FORMAT[target]
        or expected_bytes is None
        or expected_bytes < 1
        or expected_bytes > MAX_OUTPUT_BYTES
        or expected_duration is None
        or _safe_int(output_channels) not in {1, 2}
        or _safe_int(output_sample_rate) != 48_000
        or str(output_codec or "") != OUTPUT_CODEC_BY_FORMAT[target]
        or SHA256_PATTERN.fullmatch(str(digest or "").lower()) is None
    ):
        return False
    try:
        path = _output_path(audio_asset_operations_directory(), str(storage_key or ""), expected_format=target)
        _verify_output_path(
            path,
            target_format=target,
            expected_bytes=expected_bytes,
            expected_digest=str(digest or ""),
            expected_duration_seconds=expected_duration / 1000.0,
        )
        return True
    except (AudioAssetOperationError, OSError, RuntimeError, ValueError):
        return False


def _operation_envelope(operation: dict[str, Any], *, replay: bool = False) -> dict[str, Any]:
    state = str(operation.get("state") or "guarded")
    kind = str(operation.get("kind") or "")
    if state == "completed" and kind == AUDIO_INSPECT_KIND:
        return envelope(
            True,
            "Đã kiểm định audio private. Thao tác này không tạo file đầu ra.",
            data={"operation": operation, "replay": replay},
            status_name="completed",
        )
    if state == "completed" and kind in TRANSFORM_KINDS and operation.get("output_available") is True:
        label = "chuẩn hóa" if kind == AUDIO_NORMALIZE_KIND else "chuyển đổi"
        return envelope(
            True,
            f"Đã {label} audio private và xác minh output.",
            data={"operation": operation, "replay": replay},
            status_name="completed",
        )
    if state == "completed" and kind in TRANSFORM_KINDS:
        return envelope(
            False,
            "Output audio private chưa qua xác minh để phát an toàn.",
            data={"operation": operation, "replay": replay},
            status_name="unavailable",
            error_code="WEB_AUDIO_ASSET_OUTPUT_UNAVAILABLE",
        )
    if state in {"queued", "processing"}:
        return envelope(
            False,
            "Audio private đang xử lý; chưa có output để tải trước khi xác minh.",
            data={"operation": operation, "replay": replay},
            status_name=state,
            error_code="WEB_AUDIO_ASSET_OPERATION_PENDING",
        )
    return envelope(
        False,
        "Không thể xử lý audio private an toàn.",
        data={"operation": operation, "replay": replay},
        status_name=state if state in OPERATION_STATES else "guarded",
        error_code="WEB_AUDIO_ASSET_OPERATION_FAILED",
    )


def _execute_operation(
    operation_id: str,
    account_id: str,
    *,
    ffmpeg: str,
    ffprobe: str,
    request_id: str,
) -> dict[str, Any]:
    source_copy: Path | None = None
    rendered: Path | None = None
    final_path: Path | None = None
    acquired = False
    try:
        claim = _claim_operation(operation_id, account_id, request_id=request_id)
        if claim is None:
            with transaction() as conn:
                row = _operation_row(conn, operation_id=operation_id, account_id=account_id)
            return _operation_public_with_verified_output(tuple(row)) if row else {}
        source, kind, target_format, normalization_profile = claim
        acquired = media_ffmpeg_capacity().acquire(timeout=RENDER_TIMEOUT_SECONDS)
        if not acquired:
            raise AudioAssetOperationError("Audio Asset Operations đang bận; hãy thử lại sau", code="AUDIO_RUNTIME_BUSY")
        root = audio_asset_operations_directory()
        source_copy = _staging_path(root, f".source{EXTENSION_BY_FORMAT[str(source['format'])]}")
        _copy_verified_source(source, source_copy)
        source_metadata = _probe_audio(ffprobe, source_copy)
        if kind == AUDIO_INSPECT_KIND:
            _complete_inspect(
                operation_id=operation_id,
                account_id=account_id,
                source=source,
                metadata=source_metadata,
                request_id=request_id,
            )
        elif kind in TRANSFORM_KINDS and target_format in TARGET_FORMATS:
            normalize = kind == AUDIO_NORMALIZE_KIND
            if normalize and (
                target_format != NORMALIZE_TARGET_FORMAT
                or normalization_profile != NORMALIZE_PROFILE
            ):
                raise AudioAssetOperationError("Profile chuẩn hóa audio không hợp lệ", code="AUDIO_OPERATION_INVALID")
            rendered = _staging_path(root, f".render.{target_format}")
            _render_audio(
                ffmpeg,
                source_copy,
                rendered,
                target_format=target_format,
                normalize=normalize,
            )
            final_path, storage_key, output_bytes, output_digest, output_metadata = _publish_verified_output(
                root,
                rendered,
                target_format=target_format,
                expected_duration_seconds=float(source_metadata["duration_seconds"]),
            )
            rendered = None
            completed = _complete_transform(
                operation_id=operation_id,
                account_id=account_id,
                source=source,
                source_metadata=source_metadata,
                target_format=target_format,
                storage_key=storage_key,
                output_bytes=output_bytes,
                output_digest=output_digest,
                output_metadata=output_metadata,
                request_id=request_id,
            )
            if not completed:
                _safe_unlink_private_output(final_path)
            final_path = None
        else:
            raise AudioAssetOperationError("Loại Audio Asset Operation không hợp lệ", code="AUDIO_OPERATION_INVALID")
    except AudioAssetOperationError as exc:
        _safe_unlink_private_output(final_path)
        _mark_terminal(operation_id, account_id, code=exc.code, request_id=request_id)
    except Exception:
        _safe_unlink_private_output(final_path)
        _mark_terminal(operation_id, account_id, code="AUDIO_OPERATION", request_id=request_id)
    finally:
        if acquired:
            media_ffmpeg_capacity().release()
        _safe_unlink(source_copy)
        _safe_unlink(rendered)
    with transaction() as conn:
        row = _operation_row(conn, operation_id=operation_id, account_id=account_id)
    return _operation_public_with_verified_output(tuple(row)) if row else {}


def _reserve_operation(
    *,
    account_id: str,
    source: dict[str, Any],
    kind: str,
    target_format: str | None,
    normalization_profile: str | None,
    idempotency_key: str,
    reservation_precondition: Callable[[Any, dict[str, Any]], None] | None = None,
) -> tuple[dict[str, Any], bool]:
    if kind not in SUPPORTED_KINDS:
        raise HTTPException(status_code=422, detail="Loại Audio Asset Operation không hợp lệ")
    if kind == AUDIO_INSPECT_KIND and (target_format or normalization_profile):
        raise HTTPException(status_code=422, detail="Kiểm định audio không nhận output profile")
    if kind == AUDIO_CONVERT_KIND and target_format not in TARGET_FORMATS:
        raise HTTPException(status_code=422, detail="Chuyển đổi audio cần định dạng mp3 hoặc m4a")
    if kind == AUDIO_NORMALIZE_KIND and (
        target_format != NORMALIZE_TARGET_FORMAT or normalization_profile != NORMALIZE_PROFILE
    ):
        raise HTTPException(status_code=422, detail="Chuẩn hóa audio dùng profile cố định của Web")
    fingerprint = _request_fingerprint(
        kind=kind,
        source=source,
        target_format=target_format,
        normalization_profile=normalization_profile,
    )
    with transaction() as conn:
        existing = conn.execute(
            f"""SELECT {OPERATION_SELECT}, request_fingerprint
                  FROM web_audio_asset_operations
                 WHERE account_id=? AND kind=? AND idempotency_key=?""",
            (account_id, kind, idempotency_key),
        ).fetchone()
        if existing:
            if not hmac.compare_digest(str(existing[-1] or ""), fingerprint):
                raise HTTPException(status_code=409, detail="Idempotency key đã dùng cho Audio Asset Operation khác")
            return _operation_public_with_verified_output(tuple(existing[:-1])), True
        # A higher-level Web-native flow may bind the executor to another
        # owner-scoped record (for example an active Audio Hub attachment).
        # Run that check in the very same reservation transaction, after a
        # safe replay has been recognized but before any queue row exists.
        # Direct Audio Asset Operations intentionally pass no callback and
        # retain their original behavior.
        if reservation_precondition is not None:
            reservation_precondition(conn, source)
        operation_id = str(uuid.uuid4())
        now = utc_now()
        conn.execute(
            """INSERT INTO web_audio_asset_operations
                   (id, account_id, source_asset_id, project_id, kind, target_format, normalization_profile,
                    state, idempotency_key, request_fingerprint, source_sha256, source_byte_size,
                    source_lifecycle_revision, source_format, created_at, queued_at, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                operation_id, account_id, str(source["asset_id"]), source["project_id"], kind,
                target_format, normalization_profile, idempotency_key, fingerprint,
                str(source["sha256"]), int(source["byte_size"]), int(source["lifecycle_revision"]),
                str(source["format"]), now, now, now,
            ),
        )
        _record_event(conn, operation_id=operation_id, state="queued", when=now)
        row = _operation_row(conn, operation_id=operation_id, account_id=account_id)
    if not row:
        raise RuntimeError("Không thể tạo Audio Asset Operation")
    return _operation_public(tuple(row)), False


@router.get("")
async def list_audio_asset_operations(
    limit: int = Query(default=20, ge=1, le=100),
    account: dict = Depends(require_account),
):
    _require_enabled()
    ensure_copyfast_schema()
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT {OPERATION_SELECT}
                  FROM web_audio_asset_operations
                 WHERE account_id=?
                 ORDER BY updated_at DESC, id DESC LIMIT ?""",
            (str(account["id"]), int(limit)),
        ).fetchall()
    return envelope(
        True,
        "Đã tải lịch sử Audio Asset Operations private.",
        data={"operations": [_operation_public_with_verified_output(tuple(row)) for row in rows], "source": "web_native"},
        status_name="read_only",
    )


@router.get("/{operation_id}")
async def get_audio_asset_operation(operation_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã Audio Asset Operation")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = _operation_row(conn, operation_id=operation_id, account_id=str(account["id"]))
        events = conn.execute(
            """SELECT state, created_at FROM web_audio_asset_operation_events
                 WHERE operation_id=? ORDER BY sequence ASC, id ASC LIMIT 20""",
            (operation_id,),
        ).fetchall()
    if not row:
        return envelope(
            False,
            "Không tìm thấy Audio Asset Operation.",
            status_name="guarded",
            error_code="WEB_AUDIO_ASSET_OPERATION_NOT_FOUND",
        )
    operation = _operation_public_with_verified_output(tuple(row))
    response = _operation_envelope(operation)
    response["data"]["events"] = [{"state": str(event[0]), "created_at": str(event[1])} for event in events]
    return response


async def _create_operation(
    *,
    kind: str,
    target_format: str | None,
    normalization_profile: str | None,
    source_asset_id: str,
    idempotency_key: str,
    request: Request,
    account: dict,
    reservation_precondition: Callable[[Any, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    ffmpeg, ffprobe = _require_runtime()
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with transaction() as conn:
        source = _owner_source(conn, account_id=account_id, source_asset_id=source_asset_id)
    if source is None:
        raise HTTPException(
            status_code=422,
            detail="Chỉ nhận audio Asset Vault đang hoạt động, đúng định dạng và giới hạn Audio Asset Operations",
        )
    reserved, replay = _reserve_operation(
        account_id=account_id,
        source=source,
        kind=kind,
        target_format=target_format,
        normalization_profile=normalization_profile,
        idempotency_key=idempotency_key,
        reservation_precondition=reservation_precondition,
    )
    if replay:
        return _operation_envelope(reserved, replay=True)
    operation_id = str(reserved["id"])
    operation = await run_in_threadpool(
        _execute_operation,
        operation_id,
        account_id,
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
        request_id=_request_id(request),
    )
    return _operation_envelope(operation)


async def execute_audio_asset_operation(
    *,
    kind: str,
    target_format: str | None,
    normalization_profile: str | None,
    source_asset_id: str,
    idempotency_key: str,
    request: Request,
    account: dict,
    reservation_precondition: Callable[[Any, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Execute one already-authorized private operation.

    This server-only adapter preserves the normal Audio Asset Operations
    owner/runtime/output checks while allowing a narrowly scoped Web workflow
    to add an atomic reservation-time ownership precondition.  It does not
    expose a browser-controlled callback, process option, provider, Bot,
    wallet or payment capability.
    """

    return await _create_operation(
        kind=kind,
        target_format=target_format,
        normalization_profile=normalization_profile,
        source_asset_id=source_asset_id,
        idempotency_key=idempotency_key,
        request=request,
        account=account,
        reservation_precondition=reservation_precondition,
    )


@router.post("/inspect")
async def inspect_audio_asset(
    payload: AudioAssetInspectRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    return await _create_operation(
        kind=AUDIO_INSPECT_KIND,
        target_format=None,
        normalization_profile=None,
        source_asset_id=payload.source_asset_id,
        idempotency_key=payload.idempotency_key,
        request=request,
        account=account,
    )


@router.post("/convert")
async def convert_audio_asset(
    payload: AudioAssetConvertRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    return await _create_operation(
        kind=AUDIO_CONVERT_KIND,
        target_format=payload.target_format,
        normalization_profile=None,
        source_asset_id=payload.source_asset_id,
        idempotency_key=payload.idempotency_key,
        request=request,
        account=account,
    )


@router.post("/normalize")
async def normalize_audio_asset(
    payload: AudioAssetInspectRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    return await _create_operation(
        kind=AUDIO_NORMALIZE_KIND,
        target_format=NORMALIZE_TARGET_FORMAT,
        normalization_profile=NORMALIZE_PROFILE,
        source_asset_id=payload.source_asset_id,
        idempotency_key=payload.idempotency_key,
        request=request,
        account=account,
    )


def _audio_operation_export_failure(
    *,
    operation_id: str,
    account_id: str,
    domain: AudioOperationAssetExportFailureDomain,
    code: str,
    public_message: str,
    status_name: str = "guarded",
) -> AudioOperationAssetExportSourceResult:
    return AudioOperationAssetExportSourceResult(
        source=None,
        failure=AudioOperationAssetExportFailure(
            domain=domain,
            code=code,
            public_message=public_message,
            status_name=status_name,
        ),
        _operation_id=operation_id,
        _account_id=account_id,
    )


def _audio_export_read_flags(*, directory: bool = False) -> int:
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
    if directory:
        flags |= int(getattr(os, "O_DIRECTORY", 0))
    return flags


def _audio_export_same_identity(left: Any, right: Any) -> bool:
    try:
        return (
            int(left.st_dev) != 0
            and int(left.st_ino) != 0
            and int(left.st_dev) == int(right.st_dev)
            and int(left.st_ino) == int(right.st_ino)
        )
    except (AttributeError, TypeError, ValueError):
        return False


def _open_pinned_audio_export_stream(root: Path, storage_key: str) -> BinaryIO:
    """Open one private output without accepting a browser-controlled path."""
    match = OUTPUT_STORAGE_KEY_PATTERN.fullmatch(storage_key)
    if not match:
        raise AudioAssetOperationError("Output audio không còn integrity", code="AUDIO_OUTPUT_INVALID")
    leaf = storage_key.removeprefix("outputs/")
    if not leaf or "/" in leaf or "\\" in leaf:
        raise AudioAssetOperationError("Output audio không còn integrity", code="AUDIO_OUTPUT_INVALID")
    stream: BinaryIO | None = None
    root_fd: int | None = None
    outputs_fd: int | None = None
    file_fd: int | None = None
    descriptor_open = (
        bool(getattr(os, "O_DIRECTORY", 0))
        and os.open in getattr(os, "supports_dir_fd", frozenset())
        and os.stat in getattr(os, "supports_dir_fd", frozenset())
    )
    try:
        if descriptor_open:
            root_fd = os.open(os.fspath(root), _audio_export_read_flags(directory=True))
            if not stat.S_ISDIR(os.fstat(root_fd).st_mode):
                raise AudioAssetOperationError("Vùng audio riêng tư không còn integrity", code="AUDIO_OUTPUT_INVALID")
            outputs_before = os.stat("outputs", dir_fd=root_fd, follow_symlinks=False)
            if not stat.S_ISDIR(outputs_before.st_mode):
                raise AudioAssetOperationError("Vùng audio riêng tư không còn integrity", code="AUDIO_OUTPUT_INVALID")
            outputs_fd = os.open("outputs", _audio_export_read_flags(directory=True), dir_fd=root_fd)
            if not stat.S_ISDIR(os.fstat(outputs_fd).st_mode) or not _audio_export_same_identity(outputs_before, os.fstat(outputs_fd)):
                raise AudioAssetOperationError("Vùng audio riêng tư không còn integrity", code="AUDIO_OUTPUT_INVALID")
            before = os.stat(leaf, dir_fd=outputs_fd, follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode):
                raise AudioAssetOperationError("Output audio không còn integrity", code="AUDIO_OUTPUT_INVALID")
            file_fd = os.open(leaf, _audio_export_read_flags(), dir_fd=outputs_fd)
            stream = os.fdopen(file_fd, "rb", closefd=True)
            file_fd = None
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or not _audio_export_same_identity(before, os.fstat(stream.fileno())):
                raise AudioAssetOperationError("Output audio không còn integrity", code="AUDIO_OUTPUT_INVALID")
            return stream
        outputs = root / "outputs"
        root_before = os.lstat(root)
        outputs_before = os.lstat(outputs)
        candidate = outputs / leaf
        before = os.lstat(candidate)
        if not stat.S_ISDIR(root_before.st_mode) or not stat.S_ISDIR(outputs_before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise AudioAssetOperationError("Output audio không còn integrity", code="AUDIO_OUTPUT_INVALID")
        stream = os.fdopen(os.open(candidate, _audio_export_read_flags()), "rb", closefd=True)
        if not (
            _audio_export_same_identity(root_before, os.lstat(root))
            and _audio_export_same_identity(outputs_before, os.lstat(outputs))
            and _audio_export_same_identity(before, os.lstat(candidate))
            and _audio_export_same_identity(before, os.fstat(stream.fileno()))
        ):
            raise AudioAssetOperationError("Output audio không còn integrity", code="AUDIO_OUTPUT_INVALID")
        return stream
    except AudioAssetOperationError:
        if stream is not None:
            stream.close()
        raise
    except (OSError, TypeError, ValueError) as exc:
        if stream is not None:
            stream.close()
        raise AudioAssetOperationError("Không thể mở output audio riêng tư", code="AUDIO_OUTPUT_INVALID") from exc
    finally:
        for descriptor in (file_fd, outputs_fd, root_fd):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _digest_pinned_audio_export_stream(stream: BinaryIO, *, maximum_bytes: int) -> tuple[int, str, bytes]:
    stream.seek(0)
    digest = hashlib.sha256()
    total = 0
    prefix = bytearray()
    while True:
        chunk = stream.read(CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > maximum_bytes:
            raise AudioAssetOperationError("Output audio vượt giới hạn lưu trữ", code="AUDIO_OUTPUT_LIMIT")
        if len(prefix) < 64:
            prefix.extend(chunk[: 64 - len(prefix)])
        digest.update(chunk)
    stream.seek(0)
    return total, digest.hexdigest(), bytes(prefix)


def _open_audio_operation_asset_export_source_unfenced(
    *,
    operation_id: str,
    account_id: str,
) -> AudioOperationAssetExportSourceResult:
    """Open and verify one owner-scoped completed transform for a fenced copy."""
    try:
        ensure_copyfast_schema()
        with transaction() as conn:
            row = conn.execute(
                """SELECT kind, state, target_format, normalization_profile, project_id,
                          content_type, byte_size, sha256, storage_key, original_filename,
                          output_duration_ms, output_channels, output_sample_rate, output_codec
                     FROM web_audio_asset_operations WHERE id=? AND account_id=?""",
                (operation_id, account_id),
            ).fetchone()
    except Exception:
        return _audio_operation_export_failure(
            operation_id=operation_id, account_id=account_id,
            domain=AudioOperationAssetExportFailureDomain.RETRYABLE,
            code="WEB_AUDIO_OPERATION_EXPORT_STORAGE_UNAVAILABLE",
            public_message="Chưa thể chuẩn bị lưu audio riêng tư. Hãy thử lại sau.",
        )
    if not row:
        return _audio_operation_export_failure(
            operation_id=operation_id, account_id=account_id,
            domain=AudioOperationAssetExportFailureDomain.PRECONDITION,
            code="WEB_AUDIO_OPERATION_EXPORT_NOT_READY",
            public_message="Audio chưa sẵn sàng để lưu vào Asset Vault.",
        )
    state, kind = str(row[1] or ""), str(row[0] or "")
    if state in {"queued", "processing"}:
        return _audio_operation_export_failure(
            operation_id=operation_id, account_id=account_id,
            domain=AudioOperationAssetExportFailureDomain.PRECONDITION,
            code="WEB_AUDIO_OPERATION_EXPORT_PENDING",
            public_message="Audio đang xử lý; chưa thể lưu vào Asset Vault.",
            status_name="processing",
        )
    if state != "completed" or kind not in TRANSFORM_KINDS:
        return _audio_operation_export_failure(
            operation_id=operation_id, account_id=account_id,
            domain=AudioOperationAssetExportFailureDomain.PRECONDITION,
            code="WEB_AUDIO_OPERATION_EXPORT_NOT_READY",
            public_message="Audio chưa sẵn sàng để lưu vào Asset Vault.",
        )
    target = str(row[2] or "")
    extension = EXTENSION_BY_FORMAT.get(target)
    expected_bytes = _safe_int(row[6])
    expected_duration_ms = _safe_int(row[10])
    expected_digest = str(row[7] or "").lower()
    expected_codec = OUTPUT_CODEC_BY_FORMAT.get(target)
    descriptor_valid = (
        extension is not None
        and str(row[5] or "") == MIME_BY_FORMAT[target]
        and str(row[9] or "") == OUTPUT_FILENAME_BY_FORMAT[target]
        and OUTPUT_STORAGE_KEY_PATTERN.fullmatch(str(row[8] or "")) is not None
        and str(row[8] or "").endswith(extension)
        and expected_bytes is not None and 0 < expected_bytes <= MAX_OUTPUT_BYTES
        and SHA256_PATTERN.fullmatch(expected_digest) is not None
        and expected_duration_ms is not None and expected_duration_ms >= int(MIN_DURATION_SECONDS * 1000)
        and _safe_int(row[11]) in {1, 2}
        and _safe_int(row[12]) == 48_000
        and str(row[13] or "") == expected_codec
        and ((kind == AUDIO_NORMALIZE_KIND and row[3] == NORMALIZE_PROFILE) or (kind == AUDIO_CONVERT_KIND and row[3] is None))
    )
    if not descriptor_valid:
        return _audio_operation_export_failure(
            operation_id=operation_id, account_id=account_id,
            domain=AudioOperationAssetExportFailureDomain.SOURCE_INTEGRITY,
            code="WEB_AUDIO_OPERATION_EXPORT_SOURCE_UNAVAILABLE",
            public_message="Output audio không còn integrity để lưu vào Asset Vault.",
            status_name="unavailable",
        )
    try:
        root = audio_asset_operations_directory()
    except Exception:
        return _audio_operation_export_failure(
            operation_id=operation_id, account_id=account_id,
            domain=AudioOperationAssetExportFailureDomain.RETRYABLE,
            code="WEB_AUDIO_OPERATION_EXPORT_STORAGE_UNAVAILABLE",
            public_message="Chưa thể chuẩn bị lưu audio riêng tư. Hãy thử lại sau.",
        )
    stream: BinaryIO | None = None
    try:
        stream = _open_pinned_audio_export_stream(root, str(row[8]))
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or int(opened.st_size) != expected_bytes:
            raise AudioAssetOperationError("Output audio không còn integrity", code="AUDIO_OUTPUT_INVALID")
        copied_bytes, copied_digest, prefix = _digest_pinned_audio_export_stream(stream, maximum_bytes=MAX_OUTPUT_BYTES)
        if copied_bytes != expected_bytes or not hmac.compare_digest(copied_digest, expected_digest) or not _audio_magic_matches(target, prefix):
            raise AudioAssetOperationError("Output audio không còn integrity", code="AUDIO_OUTPUT_INVALID")
        _ffmpeg, ffprobe = _audio_runtime()
        metadata = _probe_pinned_audio_export_stream(ffprobe, stream)
        if (
            not _format_name_matches(target, str(metadata["format_name"]))
            or str(metadata["codec"]) != expected_codec
            or int(metadata["duration_ms"]) != expected_duration_ms
            or int(metadata["channels"]) != int(row[11])
            or int(metadata["sample_rate"]) != int(row[12])
        ):
            raise AudioAssetOperationError("Output audio không còn integrity", code="AUDIO_OUTPUT_INVALID")
        final_bytes, final_digest, _prefix = _digest_pinned_audio_export_stream(stream, maximum_bytes=MAX_OUTPUT_BYTES)
        if final_bytes != expected_bytes or not hmac.compare_digest(final_digest, expected_digest):
            raise AudioAssetOperationError("Output audio không còn integrity", code="AUDIO_OUTPUT_INVALID")
        return AudioOperationAssetExportSourceResult(
            source=AudioOperationAssetExportPinnedSource(
                stream=stream, kind=kind, project_id=str(row[4]) if row[4] else None,
                target_format=target, extension=extension, content_type=MIME_BY_FORMAT[target],
                byte_size=expected_bytes, digest=expected_digest,
                duration_seconds=float(metadata["duration_seconds"]), duration_ms=int(metadata["duration_ms"]),
                channels=int(metadata["channels"]), sample_rate=int(metadata["sample_rate"]),
                codec=str(metadata["codec"]), format_name=str(metadata["format_name"]),
            ),
            failure=None, _operation_id=operation_id, _account_id=account_id,
        )
    except AudioAssetOperationError as exc:
        if stream is not None:
            stream.close()
        retryable = exc.code == "AUDIO_RUNTIME_UNAVAILABLE"
        return _audio_operation_export_failure(
            operation_id=operation_id, account_id=account_id,
            domain=(AudioOperationAssetExportFailureDomain.RETRYABLE if retryable else AudioOperationAssetExportFailureDomain.SOURCE_INTEGRITY),
            code="WEB_AUDIO_OPERATION_EXPORT_SOURCE_UNAVAILABLE",
            public_message=("Chưa thể kiểm tra audio để lưu vào Asset Vault. Hãy thử lại sau." if retryable else "Output audio không còn integrity để lưu vào Asset Vault."),
            status_name=("guarded" if retryable else "unavailable"),
        )
    except Exception:
        if stream is not None:
            stream.close()
        return _audio_operation_export_failure(
            operation_id=operation_id, account_id=account_id,
            domain=AudioOperationAssetExportFailureDomain.SOURCE_INTEGRITY,
            code="WEB_AUDIO_OPERATION_EXPORT_SOURCE_UNAVAILABLE",
            public_message="Output audio không còn integrity để lưu vào Asset Vault.",
            status_name="unavailable",
        )


def open_audio_operation_asset_export_source(
    *,
    operation_id: str,
    account_id: str,
) -> AudioOperationAssetExportSourceResult:
    """Verify a private export source under the existing single-media fence.

    This remains synchronous by design so it can safely hold a server-opened
    stream, but the async route always invokes it through ``run_in_threadpool``
    after it owns the account/operation export lease.  The narrow media gate
    prevents ffprobe work from competing with a running transform.
    """

    acquired = media_ffmpeg_capacity().acquire(timeout=RENDER_TIMEOUT_SECONDS)
    if not acquired:
        return _audio_operation_export_failure(
            operation_id=operation_id,
            account_id=account_id,
            domain=AudioOperationAssetExportFailureDomain.RETRYABLE,
            code="WEB_AUDIO_OPERATION_EXPORT_RUNTIME_BUSY",
            public_message="Audio Asset Operations đang bận; hãy thử lại sau.",
        )
    try:
        return _open_audio_operation_asset_export_source_unfenced(
            operation_id=operation_id,
            account_id=account_id,
        )
    finally:
        media_ffmpeg_capacity().release()


def mark_audio_operation_asset_export_source_unavailable(result: AudioOperationAssetExportSourceResult) -> bool:
    if not isinstance(result, AudioOperationAssetExportSourceResult) or not result.is_source_integrity_failure:
        return False
    _mark_output_unavailable(result._operation_id, result._account_id)
    return True


def _audio_operation_asset_export_vault_source(
    *,
    account_id: str,
    operation_id: str,
    pinned: AudioOperationAssetExportPinnedSource,
):
    from copyfast_assets import AudioOperationAssetExportSource

    return AudioOperationAssetExportSource(
        account_id=account_id,
        operation_id=operation_id,
        kind=pinned.kind,
        project_id=pinned.project_id,
        original_filename=OUTPUT_FILENAME_BY_FORMAT[pinned.target_format],
        target_format=pinned.target_format,
        extension=pinned.extension,
        content_type=pinned.content_type,
        byte_size=pinned.byte_size,
        sha256=pinned.digest,
        duration_seconds=pinned.duration_seconds,
        duration_ms=pinned.duration_ms,
        channels=pinned.channels,
        sample_rate=pinned.sample_rate,
        codec=pinned.codec,
        format_name=pinned.format_name,
        stream=pinned.stream,
    )


def _release_current_audio_export_lease(lease: Any) -> None:
    """Best-effort release of only the lease held by this request."""
    from copyfast_assets import release_audio_operation_asset_export_lease

    try:
        release_audio_operation_asset_export_lease(lease)
    except Exception:
        # A transient DB/lease failure must not mutate the completed transform
        # into an unavailable result or turn a retryable export into success.
        pass


def _audio_operation_asset_export_nonterminal_response(state: object):
    """Keep an invalidated export receipt distinct from an active copy."""

    if str(state or "") == "guarded":
        return envelope(
            False,
            "Không thể xác nhận Audio trong Asset Vault. Audio gốc vẫn giữ nguyên để bạn thử lại.",
            status_name="guarded",
            error_code="WEB_AUDIO_OPERATION_EXPORT_GUARDED",
        )
    return envelope(
        False,
        "Audio đang được lưu vào Asset Vault. Hãy tải lại sau.",
        status_name="processing",
        error_code="WEB_AUDIO_OPERATION_EXPORT_PENDING",
    )


@router.post("/{operation_id}/export-to-asset-vault")
async def export_audio_operation_to_asset_vault(
    operation_id: str,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    account: dict = Depends(require_csrf),
):
    _require_asset_export_enabled()
    operation_id = _uuid(operation_id, label="Mã Audio Asset Operation")
    account_id = str(account["id"])
    from copyfast_assets import (
        finalize_audio_operation_asset_export,
        get_audio_operation_asset_export_receipt,
        replay_audio_operation_asset_export,
        reserve_audio_operation_asset_export,
    )

    key = _idempotency_key(idempotency_key)
    replay = replay_audio_operation_asset_export(account_id=account_id, operation_id=operation_id, idempotency_key=key)
    if replay is not None:
        if replay.state == "completed" and replay.asset is not None:
            return envelope(True, "Audio đã có trong Asset Vault riêng tư.", data={"asset": replay.asset}, status_name="completed")
        return _audio_operation_asset_export_nonterminal_response(replay.state)

    try:
        # Reserve from the immutable operation row before opening, hashing or
        # probing the private output. The browser never supplies a descriptor,
        # so this transaction establishes the per-operation fence first.
        reservation = reserve_audio_operation_asset_export(
            account_id=account_id,
            operation_id=operation_id,
            idempotency_key=key,
        )
    except HTTPException as exc:
        # The reservation lookup happens before source I/O. Keep foreign or
        # malformed completed-operation state indistinguishable to callers,
        # as the old owner-scoped source opener did; quota and other explicit
        # public request errors retain their existing HTTP semantics.
        if exc.status_code in {404, 409}:
            return envelope(
                False,
                "Audio chưa sẵn sàng để lưu vào Asset Vault.",
                status_name="guarded",
                error_code="WEB_AUDIO_OPERATION_EXPORT_GUARDED",
            )
        raise
    if reservation.state != "leased" or reservation.lease is None:
        receipt = get_audio_operation_asset_export_receipt(account_id=account_id, operation_id=operation_id)
        if receipt is not None and receipt.state == "completed" and receipt.asset is not None:
            return envelope(True, "Audio đã có trong Asset Vault riêng tư.", data={"asset": receipt.asset}, status_name="completed")
        return _audio_operation_asset_export_nonterminal_response(
            "guarded" if reservation.state == "guarded" else (receipt.state if receipt is not None else reservation.state)
        )

    try:
        source_result = await run_in_threadpool(
            open_audio_operation_asset_export_source,
            operation_id=operation_id,
            account_id=account_id,
        )
    except Exception:
        _release_current_audio_export_lease(reservation.lease)
        return envelope(False, "Chưa thể kiểm tra audio để lưu vào Asset Vault. Hãy thử lại sau.", status_name="guarded", error_code="WEB_AUDIO_OPERATION_EXPORT_RETRY")
    if source_result.source is None:
        _release_current_audio_export_lease(reservation.lease)
        if source_result.is_source_integrity_failure:
            mark_audio_operation_asset_export_source_unavailable(source_result)
        failure = source_result.failure
        return envelope(False, failure.public_message if failure else "Audio chưa thể lưu vào Asset Vault.", status_name=failure.status_name if failure else "guarded", error_code=failure.code if failure else "WEB_AUDIO_OPERATION_EXPORT_GUARDED")

    pinned = source_result.source
    source_result.source = None
    vault_source = _audio_operation_asset_export_vault_source(
        account_id=account_id,
        operation_id=operation_id,
        pinned=pinned,
    )
    try:
        await run_in_threadpool(
            finalize_audio_operation_asset_export,
            lease=reservation.lease,
            source=vault_source,
            request_id=_request_id(request),
        )
        receipt = get_audio_operation_asset_export_receipt(account_id=account_id, operation_id=operation_id)
    except HTTPException:
        _release_current_audio_export_lease(reservation.lease)
        raise
    except Exception:
        _release_current_audio_export_lease(reservation.lease)
        return envelope(False, "Chưa thể lưu audio vào Asset Vault. Audio gốc vẫn giữ nguyên để bạn thử lại.", status_name="guarded", error_code="WEB_AUDIO_OPERATION_EXPORT_RETRY")
    if receipt is None or receipt.state != "completed" or receipt.asset is None:
        return envelope(False, "Chưa thể xác nhận trạng thái audio trong Asset Vault. Hãy tải lại sau.", status_name="processing", error_code="WEB_AUDIO_OPERATION_EXPORT_PENDING")
    return envelope(True, "Đã lưu audio đã xác minh vào Asset Vault riêng tư.", data={"asset": receipt.asset}, status_name="completed")


async def download_audio_asset_operation(operation_id: str, account: dict):
    """Deliver only a sealed, owner-scoped, reverified transform artifact."""

    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã Audio Asset Operation")
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            """SELECT kind, state, target_format, storage_key, content_type, byte_size, sha256,
                      output_duration_ms, output_channels, output_sample_rate, output_codec
                 FROM web_audio_asset_operations
                WHERE id=? AND account_id=?""",
            (operation_id, str(account["id"])),
        ).fetchone()
    if not row or str(row[0]) not in TRANSFORM_KINDS or str(row[1]) != "completed":
        return envelope(
            False,
            "Output audio chưa sẵn sàng để tải.",
            status_name="guarded",
            error_code="WEB_AUDIO_ASSET_OUTPUT_UNAVAILABLE",
        )
    target_format = str(row[2] or "")
    byte_size = _safe_int(row[5])
    if byte_size is None:
        _mark_output_unavailable(operation_id, str(account["id"]))
        return envelope(False, "Output audio không còn integrity để tải.", status_name="unavailable", error_code="WEB_AUDIO_ASSET_OUTPUT_UNAVAILABLE")
    verified = verified_audio_asset_output_available(
        target_format=target_format,
        storage_key=row[3],
        content_type=row[4],
        byte_size=byte_size,
        digest=row[6],
        output_duration_ms=row[7],
        output_channels=row[8],
        output_sample_rate=row[9],
        output_codec=row[10],
    )
    if not verified:
        _mark_output_unavailable(operation_id, str(account["id"]))
        return envelope(False, "Output audio không còn integrity để tải.", status_name="unavailable", error_code="WEB_AUDIO_ASSET_OUTPUT_UNAVAILABLE")
    try:
        path = _output_path(audio_asset_operations_directory(), str(row[3] or ""), expected_format=target_format)
        stream = path.open("rb")
        sealed = seal_verified_private_file(
            stream,
            expected_bytes=byte_size,
            expected_digest=str(row[6] or ""),
        )
    except (OSError, RuntimeError, ValueError):
        sealed = None
    if sealed is None:
        _mark_output_unavailable(operation_id, str(account["id"]))
        return envelope(False, "Output audio không còn integrity để tải.", status_name="unavailable", error_code="WEB_AUDIO_ASSET_OUTPUT_UNAVAILABLE")
    return private_asset_attachment_response(
        sealed,
        byte_size=byte_size,
        media_type=MIME_BY_FORMAT[target_format],
        filename=OUTPUT_FILENAME_BY_FORMAT[target_format],
    )


@router.get("/{operation_id}/download")
async def download_audio_asset_operation_route(operation_id: str, account: dict = Depends(require_account)):
    return await download_audio_asset_operation(operation_id, account)


def reconcile_audio_asset_operation_storage(*, interrupted_before: str | None = None) -> None:
    """Fail stale operations closed and verify old local outputs after startup."""

    if not audio_asset_operations_enabled():
        return
    try:
        root = audio_asset_operations_directory()
    except RuntimeError:
        return
    ensure_copyfast_schema()
    cutoff = interrupted_before or utc_now()
    with transaction() as conn:
        stale = conn.execute(
            """SELECT id, account_id FROM web_audio_asset_operations
                 WHERE state IN ('queued', 'processing') AND created_at<?""",
            (cutoff,),
        ).fetchall()
        completed = conn.execute(
            """SELECT id, account_id, target_format, storage_key, content_type, byte_size, sha256,
                      output_duration_ms, output_channels, output_sample_rate, output_codec
                 FROM web_audio_asset_operations
                WHERE state='completed' AND kind IN (?, ?)""",
            (AUDIO_CONVERT_KIND, AUDIO_NORMALIZE_KIND),
        ).fetchall()
    for operation_id, account_id in stale:
        _mark_terminal(str(operation_id), str(account_id), code="AUDIO_OPERATION_INTERRUPTED", request_id="system:audio_asset_reconcile")
    for row in completed:
        if not verified_audio_asset_output_available(
            target_format=row[2],
            storage_key=row[3],
            content_type=row[4],
            byte_size=row[5],
            digest=row[6],
            output_duration_ms=row[7],
            output_channels=row[8],
            output_sample_rate=row[9],
            output_codec=row[10],
        ):
            _mark_output_unavailable(str(row[0]), str(row[1]))
    staging = _private_directory(root, ".staging")
    threshold = datetime.now(timezone.utc) - timedelta(seconds=ORPHAN_RETENTION_SECONDS)
    for entry in staging.iterdir():
        try:
            modified = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
        except OSError:
            continue
        if modified < threshold:
            _safe_unlink(entry)
