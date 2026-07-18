"""Private, deterministic Storyboard Grid Splitter for the standalone Web App.

This transfers the useful local crop semantics from the Telegram Bot's
``crop_storyboard_grid_to_assets`` helper without inheriting its operator-only
job state, mutable upload paths, partial asset writes, provider calls or
Telegram notifications.  A signed Web account selects one Asset Vault image;
the server creates a verified private ZIP containing deterministic JPEG scene
cells and a compact manifest.  No Bot, provider, PayOS, Xu ledger, job queue
or browser canvas participates in this module.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from io import BytesIO
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any
import uuid
import warnings
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from copyfast_assets import open_verified_private_asset_stream
from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import (
    asset_vault_enabled,
    ensure_copyfast_schema,
    image_operations_directory,
    image_operations_enabled,
    storyboard_grid_enabled,
    transaction,
    utc_now,
)
from copyfast_image_runtime import image_decoder_capacity


router = APIRouter(prefix="/api/v1/storyboard-grid", tags=["Storyboard Grid Splitter"])

KIND = "storyboard_grid_split"
STATE_VALUES = frozenset({"queued", "processing", "completed", "failed", "unavailable", "guarded"})
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
# Match the same canonical UUID form already used by Asset Vault and Image
# Operations: 8-4-4-4-12 hex groups.  Keep the RFC version/variant fence,
# but never accidentally concatenate the last two groups (which would reject
# every valid Asset Vault ID before ownership lookup).
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
ASSET_STORAGE_KEY_PATTERN = re.compile(r"^objects/[0-9a-f]{32}\.blob$")
OUTPUT_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.zip$")

IMAGE_MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
JPEG_MEDIA_TYPE = "image/jpeg"
ZIP_MEDIA_TYPE = "application/zip"
ZIP_FILENAME = "toan-aas-storyboard-grid.zip"
MANIFEST_FILENAME = "manifest.json"
MANIFEST_VERSION = "toan-aas-storyboard-grid-v1"

MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_SOURCE_DIMENSION = 7_680
MAX_SOURCE_PIXELS = 16 * 1024 * 1024
MAX_SOURCE_ASPECT_RATIO = 12
MAX_ROWS = 6
MAX_COLS = 8
MAX_CELLS = 48
MIN_CELL_DIMENSION = 32
MAX_EPISODE = 9_999
MAX_START_SCENE = 9_999
MAX_SCENE_NUMBER = 19_999
MAX_TRIM_PERCENT = 0.18
JPEG_QUALITY = 94
CHUNK_BYTES = 1024 * 1024
ORPHAN_RETENTION_SECONDS = 60 * 60

OPERATION_SELECT = """id, account_id, source_asset_id, project_id, state, idempotency_key,
                      request_fingerprint, source_sha256, source_byte_size, source_width,
                      source_height, rows, cols, episode, start_scene, trim_percent,
                      scene_count, storage_key, original_filename, content_type, byte_size,
                      sha256, failure_code, created_at, queued_at, started_at, completed_at,
                      updated_at"""
CELL_SELECT = """id, operation_id, scene_no, row_index, column_index, crop_x, crop_y,
                 width, height, original_filename, byte_size, sha256"""


class StoryboardGridError(Exception):
    """A bounded failure whose message is safe to show to the signed owner."""

    def __init__(self, message: str, *, code: str = "STORYBOARD_GRID_INVALID"):
        super().__init__(message)
        self.public_message = message
        self.code = code


class StoryboardGridRequest(BaseModel):
    """One immutable Asset Vault image becomes a private scene archive."""

    model_config = ConfigDict(extra="forbid")

    source_asset_id: str = Field(min_length=36, max_length=36)
    episode: int = Field(default=1, ge=1, le=MAX_EPISODE)
    rows: int = Field(default=2, ge=1, le=MAX_ROWS)
    cols: int = Field(default=5, ge=1, le=MAX_COLS)
    start_scene: int = Field(default=1, ge=1, le=MAX_START_SCENE)
    trim_percent: float = Field(default=0.0, ge=0.0, le=MAX_TRIM_PERCENT)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("source_asset_id")
    @classmethod
    def validate_source_asset_id(cls, value: str) -> str:
        return _uuid(value, label="Asset Vault ID")

    @field_validator("trim_percent")
    @classmethod
    def validate_trim_percent(cls, value: float) -> float:
        normalized = float(value)
        if not math.isfinite(normalized):
            raise ValueError("Trim storyboard phải là số hữu hạn")
        return round(normalized, 6)

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str) -> str:
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
    if not image_operations_enabled() or not asset_vault_enabled():
        raise HTTPException(
            status_code=503,
            detail="Storyboard Grid Splitter cần Asset Vault private và Image Operations storage đã được bật",
        )
    if not storyboard_grid_enabled():
        raise HTTPException(
            status_code=503,
            detail="Storyboard Grid Splitter chưa được bật; cần WEBAPP_STORYBOARD_GRID_ENABLED và private storage",
        )


def ensure_storyboard_grid_runtime() -> None:
    """Fail closed when this explicitly enabled feature lacks Pillow."""
    if not storyboard_grid_enabled():
        return
    _image_classes()


def _image_classes():
    try:
        from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError
    except ImportError as exc:  # pragma: no cover - deployment configuration
        raise StoryboardGridError(
            "Storyboard Grid Splitter chưa có runtime Pillow an toàn",
            code="STORYBOARD_GRID_RUNTIME_UNAVAILABLE",
        ) from exc
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    return Image, ImageFile, ImageOps, UnidentifiedImageError


def _maximum_output_bytes() -> int:
    raw = os.environ.get("WEBAPP_STORYBOARD_GRID_MAX_OUTPUT_MB", "30").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 30
    return max(1, min(megabytes, 100)) * 1024 * 1024


def _maximum_account_bytes() -> int:
    raw = os.environ.get("WEBAPP_IMAGE_OPERATIONS_QUOTA_MB", "100").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 100
    return max(1, min(megabytes, 5_000)) * 1024 * 1024


def _feature_root() -> Path:
    parent = image_operations_directory().resolve()
    candidate = parent / "storyboard-grid"
    if candidate.exists() and candidate.is_symlink():
        raise RuntimeError("Storage Storyboard Grid không được là symbolic link")
    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise RuntimeError("Storage Storyboard Grid không hợp lệ")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(parent)
    except ValueError as exc:
        raise RuntimeError("Storage Storyboard Grid vượt ngoài Image Operations root") from exc
    return resolved


def _private_directory(root: Path, name: str) -> Path:
    if name not in {".staging", "outputs"}:
        raise RuntimeError("Thư mục Storyboard Grid không hợp lệ")
    candidate = root / name
    if candidate.exists() and candidate.is_symlink():
        raise RuntimeError("Thư mục Storyboard Grid không được là symbolic link")
    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise RuntimeError("Thư mục Storyboard Grid không hợp lệ")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError("Thư mục Storyboard Grid vượt ngoài storage riêng") from exc
    return resolved


def _staging_path(root: Path, suffix: str) -> Path:
    return _private_directory(root, ".staging") / f"{uuid.uuid4().hex}{suffix}"


def _output_path(root: Path, storage_key: str) -> Path:
    if not OUTPUT_STORAGE_KEY_PATTERN.fullmatch(str(storage_key or "")):
        raise RuntimeError("Storage key Storyboard Grid không hợp lệ")
    candidate = root / str(storage_key)
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError("Storage key Storyboard Grid vượt ngoài storage riêng") from exc
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


def _asset_source_is_valid(row: tuple[Any, ...] | None) -> bool:
    if not row or str(row[7] or "") != "active":
        return False
    extension = str(row[2] or "").lower()
    expected_mime = IMAGE_MIME_BY_EXTENSION.get(extension)
    byte_size = int(row[4] or 0)
    digest = str(row[5] or "")
    storage_key = str(row[6] or "")
    return (
        expected_mime is not None
        and str(row[3] or "") == expected_mime
        and 1 <= byte_size <= MAX_INPUT_BYTES
        and re.fullmatch(r"[0-9a-f]{64}", digest) is not None
        and ASSET_STORAGE_KEY_PATTERN.fullmatch(storage_key) is not None
    )


def _source_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy ảnh private đang hoạt động thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_STORYBOARD_GRID_SOURCE_NOT_FOUND",
    )


def _operation_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy Storyboard Grid thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_STORYBOARD_GRID_NOT_FOUND",
    )


def _operation_unavailable() -> dict[str, Any]:
    return envelope(
        False,
        "Storyboard Grid đầu ra không còn sẵn sàng để tải. Hãy tạo lại từ ảnh private.",
        status_name="guarded",
        error_code="WEB_STORYBOARD_GRID_UNAVAILABLE",
    )


def _normalized_spec(payload: StoryboardGridRequest) -> dict[str, int | float]:
    rows = int(payload.rows)
    cols = int(payload.cols)
    scene_count = rows * cols
    if scene_count < 1 or scene_count > MAX_CELLS:
        raise HTTPException(status_code=422, detail=f"Lưới storyboard chỉ nhận tối đa {MAX_CELLS} cảnh trong một lần tách")
    start_scene = int(payload.start_scene)
    if start_scene + scene_count - 1 > MAX_SCENE_NUMBER:
        raise HTTPException(status_code=422, detail="Số cảnh cuối vượt giới hạn an toàn của Storyboard Grid")
    return {
        "episode": int(payload.episode),
        "rows": rows,
        "cols": cols,
        "start_scene": start_scene,
        "trim_percent": round(float(payload.trim_percent), 6),
        "scene_count": scene_count,
    }


def _request_fingerprint(
    *,
    source_asset_id: str,
    source_sha256: str,
    source_bytes: int,
    spec: dict[str, int | float],
) -> str:
    payload = json.dumps(
        {
            "kind": KIND,
            "source_asset_id": source_asset_id,
            "source_sha256": source_sha256,
            "source_bytes": source_bytes,
            "episode": int(spec["episode"]),
            "rows": int(spec["rows"]),
            "cols": int(spec["cols"]),
            "start_scene": int(spec["start_scene"]),
            "trim_percent": float(spec["trim_percent"]),
            "output_format": "zip-jpeg-manifest-v1",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _spec_from_operation(row: tuple[Any, ...]) -> dict[str, int | float]:
    return {
        "rows": int(row[11]),
        "cols": int(row[12]),
        "episode": int(row[13]),
        "start_scene": int(row[14]),
        "trim_percent": round(float(row[15]), 6),
        "scene_count": int(row[16]),
    }


def _record_event(conn, *, operation_id: str, state: str, when: str | None = None) -> None:
    if state not in STATE_VALUES:
        raise RuntimeError("Trạng thái Storyboard Grid không hợp lệ")
    sequence_row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 FROM web_storyboard_grid_events WHERE operation_id=?",
        (operation_id,),
    ).fetchone()
    sequence = int(sequence_row[0] or 1) if sequence_row else 1
    conn.execute(
        """INSERT INTO web_storyboard_grid_events (id, operation_id, state, sequence, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), operation_id, state, sequence, when or utc_now()),
    )


def _public_cell(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": str(row[0]),
        "scene_no": int(row[2]),
        "row": int(row[3]),
        "column": int(row[4]),
        "width": int(row[7]),
        "height": int(row[8]),
        "original_filename": str(row[9]),
        "byte_size": int(row[10]),
        "download_ready": True,
    }


def _public_operation(row: tuple[Any, ...], cells: list[tuple[Any, ...]] | None = None) -> dict[str, Any]:
    state = str(row[4])
    result: dict[str, Any] = {
        "id": str(row[0]),
        "source_asset_id": str(row[2]),
        "project_id": str(row[3]) if row[3] else None,
        "kind": KIND,
        "state": state,
        "source_width": int(row[9]) if row[9] is not None else None,
        "source_height": int(row[10]) if row[10] is not None else None,
        "rows": int(row[11]),
        "cols": int(row[12]),
        "episode": int(row[13]),
        "start_scene": int(row[14]),
        "trim_percent": float(row[15]),
        "scene_count": int(row[16]),
        "original_filename": str(row[18]) if row[18] else None,
        "content_type": str(row[19]) if row[19] else None,
        "byte_size": int(row[20]) if row[20] is not None else None,
        "created_at": str(row[23]),
        "queued_at": str(row[24]),
        "started_at": str(row[25]) if row[25] else None,
        "completed_at": str(row[26]) if row[26] else None,
        "updated_at": str(row[27]),
        "download_ready": state == "completed" and bool(row[17]) and row[20] is not None,
    }
    if cells is not None:
        result["cells"] = [_public_cell(cell) for cell in cells]
    return result


def _operation_response(operation: dict[str, Any]) -> dict[str, Any]:
    state = str(operation.get("state") or "failed")
    if state == "completed":
        return envelope(True, "Đã tách và xác minh Storyboard Grid riêng tư.", data={"operation": operation}, status_name="completed")
    if state in {"queued", "processing"}:
        return envelope(True, "Storyboard Grid đang được máy chủ xử lý.", data={"operation": operation}, status_name=state)
    if state == "guarded":
        return envelope(False, "Storyboard Grid đã được chặn an toàn; không có output thay thế.", data={"operation": operation}, status_name="guarded", error_code="WEB_STORYBOARD_GRID_GUARDED")
    return envelope(False, "Storyboard Grid không hoàn tất; không có output được phát hành.", data={"operation": operation}, status_name=state, error_code="WEB_STORYBOARD_GRID_FAILED")


def _error_status(code: str) -> int:
    if code in {"STORYBOARD_GRID_INPUT_LIMIT", "STORYBOARD_GRID_DIMENSION_LIMIT", "STORYBOARD_GRID_OUTPUT_LIMIT"}:
        return 413
    if code in {"STORYBOARD_GRID_RUNTIME_UNAVAILABLE", "STORYBOARD_GRID_STAGING_UNAVAILABLE"}:
        return 503
    return 422


def _quota_available(conn, *, account_id: str, additional_bytes: int) -> bool:
    row = conn.execute(
        """SELECT COALESCE(SUM(byte_size), 0)
           FROM web_storyboard_grid_operations
           WHERE account_id=? AND state='completed' AND byte_size IS NOT NULL""",
        (account_id,),
    ).fetchone()
    used = int(row[0] or 0) if row else 0
    return used + additional_bytes <= _maximum_account_bytes()


def _mark_failed(operation_id: str, account_id: str, *, request: Request, code: str) -> None:
    if not operation_id:
        return
    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            "SELECT state FROM web_storyboard_grid_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
        if not row or str(row[0]) not in {"queued", "processing"}:
            return
        conn.execute(
            """UPDATE web_storyboard_grid_operations
               SET state='failed', failure_code=?, updated_at=?
               WHERE id=? AND account_id=?""",
            (code[:80], now, operation_id, account_id),
        )
        _record_event(conn, operation_id=operation_id, state="failed", when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action="web.storyboard_grid.failed",
            request_id=_request_id(request),
            target=operation_id,
            detail=f"code={code[:80]}",
        )


def _mark_output_unavailable(operation_id: str, account_id: str) -> None:
    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            "SELECT state FROM web_storyboard_grid_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
        if not row or str(row[0]) != "completed":
            return
        conn.execute(
            """UPDATE web_storyboard_grid_operations
               SET state='unavailable', failure_code='STORYBOARD_GRID_OUTPUT_UNAVAILABLE', updated_at=?
               WHERE id=? AND account_id=?""",
            (now, operation_id, account_id),
        )
        _record_event(conn, operation_id=operation_id, state="unavailable", when=now)


def _mark_source_unavailable(asset_id: str, account_id: str) -> None:
    if not asset_id:
        return
    with transaction() as conn:
        conn.execute(
            """UPDATE web_asset_files
               SET state='unavailable', updated_at=?, lifecycle_revision=lifecycle_revision + 1
               WHERE id=? AND account_id=? AND state='active'""",
            (utc_now(), asset_id, account_id),
        )


def _copy_verified_source(
    destination: Path,
    *,
    storage_key: str,
    expected_bytes: int,
    expected_digest: str,
) -> None:
    """Stream a descriptor-verified Asset Vault blob into isolated staging."""
    stream = open_verified_private_asset_stream(
        storage_key=storage_key,
        expected_bytes=expected_bytes,
        expected_digest=expected_digest,
    )
    if stream is None:
        raise StoryboardGridError("Ảnh nguồn không còn vượt qua kiểm tra integrity", code="STORYBOARD_GRID_SOURCE_UNAVAILABLE")
    total = 0
    try:
        try:
            with destination.open("xb") as output:
                while True:
                    chunk = stream.read(CHUNK_BYTES)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > expected_bytes:
                        raise StoryboardGridError("Ảnh nguồn không còn vượt qua kiểm tra integrity", code="STORYBOARD_GRID_SOURCE_UNAVAILABLE")
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        except StoryboardGridError:
            raise
        except OSError as exc:
            raise StoryboardGridError(
                "Không thể chuẩn bị vùng xử lý ảnh riêng tư",
                code="STORYBOARD_GRID_STAGING_UNAVAILABLE",
            ) from exc
    finally:
        stream.close()
    if total != expected_bytes:
        raise StoryboardGridError("Ảnh nguồn không còn vượt qua kiểm tra integrity", code="STORYBOARD_GRID_SOURCE_UNAVAILABLE")


def _format_matches(extension: str, image_format: str | None) -> bool:
    expected = {
        ".jpg": {"JPEG"},
        ".jpeg": {"JPEG"},
        ".png": {"PNG"},
        ".webp": {"WEBP"},
    }.get(extension, set())
    return str(image_format or "").upper() in expected


def _validate_source_geometry(width: int, height: int) -> None:
    if width < 1 or height < 1:
        raise StoryboardGridError("Kích thước ảnh storyboard không hợp lệ", code="STORYBOARD_GRID_DIMENSION_LIMIT")
    if width > MAX_SOURCE_DIMENSION or height > MAX_SOURCE_DIMENSION:
        raise StoryboardGridError(
            f"Cạnh dài ảnh storyboard vượt giới hạn {MAX_SOURCE_DIMENSION} px",
            code="STORYBOARD_GRID_DIMENSION_LIMIT",
        )
    if width * height > MAX_SOURCE_PIXELS:
        raise StoryboardGridError("Độ phân giải ảnh storyboard vượt giới hạn xử lý an toàn", code="STORYBOARD_GRID_DIMENSION_LIMIT")
    if max(width, height) / min(width, height) > MAX_SOURCE_ASPECT_RATIO:
        raise StoryboardGridError("Tỷ lệ khung hình storyboard vượt giới hạn xử lý an toàn", code="STORYBOARD_GRID_DIMENSION_LIMIT")


def _inspect_geometry(source_copy: Path, *, extension: str) -> tuple[int, int]:
    """Verify source bytes and return EXIF-normalized dimensions before a row exists."""
    Image, ImageFile, ImageOps, UnidentifiedImageError = _image_classes()
    if ImageFile.LOAD_TRUNCATED_IMAGES:
        raise StoryboardGridError("Image runtime không ở chế độ kiểm tra đầy đủ", code="STORYBOARD_GRID_RUNTIME_UNAVAILABLE")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source_copy) as verifier:
                if not _format_matches(extension, verifier.format):
                    raise StoryboardGridError("Định dạng ảnh nguồn không khớp Asset Vault", code="STORYBOARD_GRID_SOURCE_INVALID")
                if int(getattr(verifier, "n_frames", 1) or 1) != 1 or bool(getattr(verifier, "is_animated", False)):
                    raise StoryboardGridError("Ảnh động chưa được hỗ trợ trong Storyboard Grid", code="STORYBOARD_GRID_ANIMATED")
                width, height = int(verifier.size[0]), int(verifier.size[1])
                try:
                    orientation = int(verifier.getexif().get(274, 1) or 1)
                except (AttributeError, TypeError, ValueError):
                    orientation = 1
                if orientation in {5, 6, 7, 8}:
                    width, height = height, width
                _validate_source_geometry(width, height)
                verifier.verify()
        return width, height
    except StoryboardGridError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise StoryboardGridError("Độ phân giải ảnh storyboard vượt giới hạn xử lý an toàn", code="STORYBOARD_GRID_DIMENSION_LIMIT") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise StoryboardGridError("Ảnh storyboard không hợp lệ hoặc bị hỏng", code="STORYBOARD_GRID_SOURCE_INVALID") from exc


def _grid_cells_for_geometry(
    *,
    source_width: int,
    source_height: int,
    spec: dict[str, int | float],
) -> list[dict[str, int]]:
    """Copy Bot's row-major/round/floor-trim maths, then add safe cell floors."""
    rows = int(spec["rows"])
    cols = int(spec["cols"])
    episode = int(spec["episode"])
    start_scene = int(spec["start_scene"])
    trim_percent = float(spec["trim_percent"])
    cells: list[dict[str, int]] = []
    cell_width = source_width / cols
    cell_height = source_height / rows
    for row_index in range(rows):
        for column_index in range(cols):
            scene_no = start_scene + (row_index * cols) + column_index
            x0 = int(round(column_index * cell_width))
            y0 = int(round(row_index * cell_height))
            x1 = int(round((column_index + 1) * cell_width))
            y1 = int(round((row_index + 1) * cell_height))
            trim_x = int((x1 - x0) * trim_percent)
            trim_y = int((y1 - y0) * trim_percent)
            crop_x = x0 + trim_x
            crop_y = y0 + trim_y
            crop_width = (x1 - trim_x) - crop_x
            crop_height = (y1 - trim_y) - crop_y
            if crop_width < MIN_CELL_DIMENSION or crop_height < MIN_CELL_DIMENSION:
                raise StoryboardGridError(
                    f"Lưới {rows} × {cols} với trim đã chọn tạo cảnh nhỏ hơn {MIN_CELL_DIMENSION} px",
                    code="STORYBOARD_GRID_CELL_TOO_SMALL",
                )
            cells.append(
                {
                    "scene_no": scene_no,
                    "row_index": row_index + 1,
                    "column_index": column_index + 1,
                    "crop_x": crop_x,
                    "crop_y": crop_y,
                    "width": crop_width,
                    "height": crop_height,
                    "episode": episode,
                }
            )
    if len(cells) != int(spec["scene_count"]):
        raise StoryboardGridError("Lưới storyboard không khớp số cảnh đã xác nhận", code="STORYBOARD_GRID_INVALID")
    return cells


def _scene_filename(*, episode: int, scene_no: int) -> str:
    # Unlike the Bot's timestamped operator upload name, Web output must be
    # idempotent and package-friendly.  This is a derived filename only.
    return f"ep{episode:02d}_scene{scene_no:02d}.jpg"


def _decode_normalized_rgb(source_copy: Path, *, extension: str, expected_width: int, expected_height: int):
    Image, _, ImageOps, UnidentifiedImageError = _image_classes()
    canvas = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source_copy) as decoded:
                if not _format_matches(extension, decoded.format):
                    raise StoryboardGridError("Định dạng ảnh nguồn không khớp Asset Vault", code="STORYBOARD_GRID_SOURCE_INVALID")
                if int(getattr(decoded, "n_frames", 1) or 1) != 1 or bool(getattr(decoded, "is_animated", False)):
                    raise StoryboardGridError("Ảnh động chưa được hỗ trợ trong Storyboard Grid", code="STORYBOARD_GRID_ANIMATED")
                decoded.load()
                normalized = ImageOps.exif_transpose(decoded)
                try:
                    rgba = normalized.convert("RGBA")
                finally:
                    if normalized is not decoded:
                        normalized.close()
                try:
                    canvas = Image.new("RGB", rgba.size, (255, 255, 255))
                    alpha = rgba.getchannel("A")
                    try:
                        canvas.paste(rgba, mask=alpha)
                    finally:
                        alpha.close()
                finally:
                    rgba.close()
        if canvas is None or canvas.size != (expected_width, expected_height):
            if canvas is not None:
                canvas.close()
            raise StoryboardGridError("Kích thước storyboard thay đổi trong khi xử lý", code="STORYBOARD_GRID_SOURCE_INVALID")
        return canvas
    except StoryboardGridError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise StoryboardGridError("Độ phân giải ảnh storyboard vượt giới hạn xử lý an toàn", code="STORYBOARD_GRID_DIMENSION_LIMIT") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise StoryboardGridError("Không thể decode ảnh storyboard an toàn", code="STORYBOARD_GRID_SOURCE_INVALID") from exc


def _verify_jpeg_bytes(payload: bytes, *, expected_width: int, expected_height: int) -> tuple[int, str]:
    Image, ImageFile, _, UnidentifiedImageError = _image_classes()
    if not payload or len(payload) > _maximum_output_bytes():
        raise StoryboardGridError("JPEG cảnh storyboard vượt giới hạn lưu trữ", code="STORYBOARD_GRID_OUTPUT_LIMIT")
    if ImageFile.LOAD_TRUNCATED_IMAGES:
        raise StoryboardGridError("Image runtime không ở chế độ kiểm tra đầy đủ", code="STORYBOARD_GRID_RUNTIME_UNAVAILABLE")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload)) as verifier:
                if str(verifier.format or "").upper() != "JPEG" or tuple(verifier.size) != (expected_width, expected_height):
                    raise StoryboardGridError("JPEG cảnh storyboard không khớp contract", code="STORYBOARD_GRID_OUTPUT_INVALID")
                if int(getattr(verifier, "n_frames", 1) or 1) != 1 or bool(getattr(verifier, "is_animated", False)):
                    raise StoryboardGridError("JPEG cảnh storyboard không hợp lệ", code="STORYBOARD_GRID_OUTPUT_INVALID")
                if verifier.getexif():
                    raise StoryboardGridError("JPEG cảnh storyboard mang metadata không được phép", code="STORYBOARD_GRID_OUTPUT_INVALID")
                verifier.load()
    except StoryboardGridError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise StoryboardGridError("JPEG cảnh storyboard vượt giới hạn xử lý an toàn", code="STORYBOARD_GRID_OUTPUT_LIMIT") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise StoryboardGridError("JPEG cảnh storyboard không vượt qua kiểm tra", code="STORYBOARD_GRID_OUTPUT_INVALID") from exc
    return len(payload), hashlib.sha256(payload).hexdigest()


def _manifest_bytes(
    *,
    source_width: int,
    source_height: int,
    spec: dict[str, int | float],
    cells: list[dict[str, Any]],
) -> bytes:
    # The manifest is intentionally self-contained and omits account IDs,
    # source IDs, hashes, storage keys, URLs, Bot job data and free-form notes.
    payload = {
        "format": MANIFEST_VERSION,
        "source": {"width": source_width, "height": source_height},
        "grid": {
            "episode": int(spec["episode"]),
            "rows": int(spec["rows"]),
            "cols": int(spec["cols"]),
            "start_scene": int(spec["start_scene"]),
            "trim_percent": float(spec["trim_percent"]),
            "scene_count": int(spec["scene_count"]),
        },
        "cells": [
            {
                "filename": str(cell["original_filename"]),
                "scene_no": int(cell["scene_no"]),
                "row": int(cell["row_index"]),
                "column": int(cell["column_index"]),
                "x": int(cell["crop_x"]),
                "y": int(cell["crop_y"]),
                "width": int(cell["width"]),
                "height": int(cell["height"]),
            }
            for cell in cells
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _zip_info(name: str) -> ZipInfo:
    """Use deterministic ZIP metadata; never inherit a staging file mtime."""
    info = ZipInfo(filename=name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o600 << 16
    return info


def _digest_stream(stream) -> str:
    digest = hashlib.sha256()
    stream.seek(0)
    while True:
        chunk = stream.read(CHUNK_BYTES)
        if not chunk:
            break
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest()


def _parser_copy(stream):
    try:
        stream.seek(0)
        return os.fdopen(os.dup(stream.fileno()), "rb", closefd=True)
    except (AttributeError, OSError):
        stream.seek(0)
        payload = stream.read()
        stream.seek(0)
        return BytesIO(payload)


def _archive_expected_names(cells: list[dict[str, Any]]) -> list[str]:
    names = [MANIFEST_FILENAME] + [str(cell["original_filename"]) for cell in cells]
    if len(names) != len(set(names)):
        raise StoryboardGridError("Tên cảnh storyboard không duy nhất", code="STORYBOARD_GRID_OUTPUT_INVALID")
    return names


def _verify_archive_stream(
    stream,
    *,
    expected_cells: list[dict[str, Any]],
    expected_manifest: bytes,
) -> None:
    """Verify the exact ZIP payload before it is delivered to a signed owner."""
    parser_stream = _parser_copy(stream)
    try:
        with ZipFile(parser_stream, "r") as archive:
            if archive.comment:
                raise StoryboardGridError("ZIP Storyboard Grid mang metadata không được phép", code="STORYBOARD_GRID_OUTPUT_INVALID")
            infos = archive.infolist()
            expected_names = _archive_expected_names(expected_cells)
            actual_names = [info.filename for info in infos]
            if actual_names != expected_names or any(info.is_dir() for info in infos):
                raise StoryboardGridError("ZIP Storyboard Grid có cấu trúc không hợp lệ", code="STORYBOARD_GRID_OUTPUT_INVALID")
            total_uncompressed = 0
            manifest_info = infos[0]
            if manifest_info.file_size != len(expected_manifest):
                raise StoryboardGridError("Manifest Storyboard Grid không khớp", code="STORYBOARD_GRID_OUTPUT_INVALID")
            manifest_payload = archive.read(manifest_info)
            total_uncompressed += len(manifest_payload)
            if not hmac.compare_digest(manifest_payload, expected_manifest):
                raise StoryboardGridError("Manifest Storyboard Grid không khớp", code="STORYBOARD_GRID_OUTPUT_INVALID")
            for info, expected in zip(infos[1:], expected_cells, strict=True):
                if info.file_size < 1 or info.file_size > _maximum_output_bytes():
                    raise StoryboardGridError("ZIP Storyboard Grid vượt giới hạn ảnh", code="STORYBOARD_GRID_OUTPUT_LIMIT")
                payload = archive.read(info)
                total_uncompressed += len(payload)
                if total_uncompressed > _maximum_output_bytes():
                    raise StoryboardGridError("ZIP Storyboard Grid vượt giới hạn lưu trữ", code="STORYBOARD_GRID_OUTPUT_LIMIT")
                byte_size, digest = _verify_jpeg_bytes(
                    payload,
                    expected_width=int(expected["width"]),
                    expected_height=int(expected["height"]),
                )
                if byte_size != int(expected["byte_size"]) or not hmac.compare_digest(digest, str(expected["sha256"])):
                    raise StoryboardGridError("JPEG cảnh storyboard không còn integrity", code="STORYBOARD_GRID_OUTPUT_INVALID")
    except StoryboardGridError:
        raise
    except (BadZipFile, OSError, RuntimeError, ValueError) as exc:
        raise StoryboardGridError("ZIP Storyboard Grid không vượt qua kiểm tra", code="STORYBOARD_GRID_OUTPUT_INVALID") from exc
    finally:
        parser_stream.close()
        stream.seek(0)


def _verify_archive_path(
    path: Path,
    *,
    expected_bytes: int,
    expected_digest: str,
    expected_cells: list[dict[str, Any]],
    expected_manifest: bytes,
) -> None:
    try:
        if not path.is_file() or path.is_symlink() or int(path.stat().st_size) != expected_bytes:
            raise StoryboardGridError("ZIP Storyboard Grid không còn integrity", code="STORYBOARD_GRID_OUTPUT_INVALID")
        if expected_bytes < 1 or expected_bytes > _maximum_output_bytes():
            raise StoryboardGridError("ZIP Storyboard Grid vượt giới hạn lưu trữ", code="STORYBOARD_GRID_OUTPUT_LIMIT")
        with path.open("rb") as stream:
            if not hmac.compare_digest(_digest_stream(stream), expected_digest):
                raise StoryboardGridError("ZIP Storyboard Grid không còn integrity", code="STORYBOARD_GRID_OUTPUT_INVALID")
            _verify_archive_stream(stream, expected_cells=expected_cells, expected_manifest=expected_manifest)
    except StoryboardGridError:
        raise
    except OSError as exc:
        raise StoryboardGridError("ZIP Storyboard Grid không vượt qua kiểm tra", code="STORYBOARD_GRID_OUTPUT_INVALID") from exc


def _open_verified_archive_stream(
    path: Path,
    *,
    expected_bytes: int,
    expected_digest: str,
    expected_cells: list[dict[str, Any]],
    expected_manifest: bytes,
):
    """Pin a verified ZIP descriptor against a final-component symlink swap."""
    flags = os.O_RDONLY | int(getattr(os, "O_NOFOLLOW", 0))
    stream = None
    try:
        stream = os.fdopen(os.open(path, flags), "rb", closefd=True)
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or int(metadata.st_size) != expected_bytes:
            raise StoryboardGridError("ZIP Storyboard Grid không còn integrity", code="STORYBOARD_GRID_OUTPUT_INVALID")
        if expected_bytes < 1 or expected_bytes > _maximum_output_bytes():
            raise StoryboardGridError("ZIP Storyboard Grid vượt giới hạn lưu trữ", code="STORYBOARD_GRID_OUTPUT_LIMIT")
        if not hmac.compare_digest(_digest_stream(stream), expected_digest):
            raise StoryboardGridError("ZIP Storyboard Grid không còn integrity", code="STORYBOARD_GRID_OUTPUT_INVALID")
        _verify_archive_stream(stream, expected_cells=expected_cells, expected_manifest=expected_manifest)
        return stream
    except StoryboardGridError:
        if stream is not None:
            stream.close()
        raise
    except OSError as exc:
        if stream is not None:
            stream.close()
        raise StoryboardGridError("ZIP Storyboard Grid không vượt qua kiểm tra", code="STORYBOARD_GRID_OUTPUT_INVALID") from exc


def _stream_open_file(stream):
    try:
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            yield chunk
    finally:
        stream.close()


def _render_grid_archive(
    root: Path,
    source_copy: Path,
    *,
    extension: str,
    source_width: int,
    source_height: int,
    spec: dict[str, int | float],
) -> tuple[Path, str, int, str, list[dict[str, Any]]]:
    """Crop all cells before atomically publishing one verified ZIP archive."""
    Image, _, _, _ = _image_classes()
    source = None
    temporary_cells: list[Path] = []
    temporary_zip: Path | None = None
    final_path: Path | None = None
    cells: list[dict[str, Any]] = []
    try:
        layout = _grid_cells_for_geometry(source_width=source_width, source_height=source_height, spec=spec)
        source = _decode_normalized_rgb(
            source_copy,
            extension=extension,
            expected_width=source_width,
            expected_height=source_height,
        )
        total_cell_bytes = 0
        for entry in layout:
            crop = source.crop(
                (
                    int(entry["crop_x"]),
                    int(entry["crop_y"]),
                    int(entry["crop_x"]) + int(entry["width"]),
                    int(entry["crop_y"]) + int(entry["height"]),
                )
            )
            try:
                if crop.mode != "RGB" or crop.size != (int(entry["width"]), int(entry["height"])):
                    raise StoryboardGridError("Cảnh storyboard không khớp lưới đã xác nhận", code="STORYBOARD_GRID_OUTPUT_INVALID")
                cell_path = _staging_path(root, ".scene.jpg")
                temporary_cells.append(cell_path)
                try:
                    with cell_path.open("xb") as output:
                        crop.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True, progressive=False)
                        output.flush()
                        os.fsync(output.fileno())
                except OSError as exc:
                    raise StoryboardGridError("Không thể ghi cảnh storyboard riêng tư", code="STORYBOARD_GRID_STAGING_UNAVAILABLE") from exc
                payload = cell_path.read_bytes()
                byte_size, digest = _verify_jpeg_bytes(
                    payload,
                    expected_width=int(entry["width"]),
                    expected_height=int(entry["height"]),
                )
                total_cell_bytes += byte_size
                if total_cell_bytes > _maximum_output_bytes():
                    raise StoryboardGridError("Tổng JPEG storyboard vượt giới hạn lưu trữ", code="STORYBOARD_GRID_OUTPUT_LIMIT")
                cells.append(
                    {
                        **entry,
                        "original_filename": _scene_filename(episode=int(entry["episode"]), scene_no=int(entry["scene_no"])),
                        "byte_size": byte_size,
                        "sha256": digest,
                        "temporary_path": cell_path,
                    }
                )
            finally:
                crop.close()
        if len(cells) != int(spec["scene_count"]):
            raise StoryboardGridError("Không thể tạo đủ cảnh storyboard", code="STORYBOARD_GRID_OUTPUT_INVALID")
        manifest = _manifest_bytes(source_width=source_width, source_height=source_height, spec=spec, cells=cells)
        temporary_zip = _staging_path(root, ".storyboard.zip")
        try:
            with ZipFile(temporary_zip, "x", compression=ZIP_DEFLATED, compresslevel=9) as archive:
                archive.writestr(_zip_info(MANIFEST_FILENAME), manifest)
                for cell in cells:
                    archive.writestr(_zip_info(str(cell["original_filename"])), Path(cell["temporary_path"]).read_bytes())
        except OSError as exc:
            raise StoryboardGridError("Không thể đóng gói Storyboard Grid an toàn", code="STORYBOARD_GRID_STAGING_UNAVAILABLE") from exc
        zip_bytes = int(temporary_zip.stat().st_size)
        if zip_bytes < 1 or zip_bytes > _maximum_output_bytes():
            raise StoryboardGridError("ZIP Storyboard Grid vượt giới hạn lưu trữ", code="STORYBOARD_GRID_OUTPUT_LIMIT")
        with temporary_zip.open("rb") as stream:
            zip_digest = _digest_stream(stream)
            _verify_archive_stream(stream, expected_cells=cells, expected_manifest=manifest)
        storage_key = f"outputs/{uuid.uuid4().hex}.zip"
        final_path = _output_path(root, storage_key)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        if final_path.exists() or final_path.is_symlink():
            raise StoryboardGridError("Không thể chuẩn bị ZIP Storyboard Grid riêng tư", code="STORYBOARD_GRID_OUTPUT_INVALID")
        os.replace(temporary_zip, final_path)
        temporary_zip = None
        _verify_archive_path(
            final_path,
            expected_bytes=zip_bytes,
            expected_digest=zip_digest,
            expected_cells=cells,
            expected_manifest=manifest,
        )
        for cell in cells:
            cell.pop("temporary_path", None)
            cell.pop("episode", None)
        return final_path, storage_key, zip_bytes, zip_digest, cells
    except StoryboardGridError:
        _safe_unlink(final_path)
        raise
    except (OSError, ValueError) as exc:
        _safe_unlink(final_path)
        raise StoryboardGridError("Không thể tạo Storyboard Grid an toàn", code="STORYBOARD_GRID_OUTPUT_INVALID") from exc
    finally:
        if source is not None:
            source.close()
        _safe_unlink(temporary_zip)
        _safe_unlink_all(temporary_cells)


def _expected_cells_from_rows(rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    return [
        {
            "scene_no": int(row[2]),
            "row_index": int(row[3]),
            "column_index": int(row[4]),
            "crop_x": int(row[5]),
            "crop_y": int(row[6]),
            "width": int(row[7]),
            "height": int(row[8]),
            "original_filename": str(row[9]),
            "byte_size": int(row[10]),
            "sha256": str(row[11]),
        }
        for row in rows
    ]


def _manifest_for_operation(operation: tuple[Any, ...], cells: list[tuple[Any, ...]]) -> bytes:
    return _manifest_bytes(
        source_width=int(operation[9]),
        source_height=int(operation[10]),
        spec=_spec_from_operation(operation),
        cells=_expected_cells_from_rows(cells),
    )


def _cells_for_operations(conn, operation_ids: list[str]) -> dict[str, list[tuple[Any, ...]]]:
    if not operation_ids:
        return {}
    placeholders = ", ".join("?" for _ in operation_ids)
    rows = conn.execute(
        f"""SELECT {CELL_SELECT} FROM web_storyboard_grid_cells
            WHERE operation_id IN ({placeholders})
            ORDER BY operation_id ASC, row_index ASC, column_index ASC, id ASC""",
        tuple(operation_ids),
    ).fetchall()
    grouped: dict[str, list[tuple[Any, ...]]] = {operation_id: [] for operation_id in operation_ids}
    for row in rows:
        grouped.setdefault(str(row[1]), []).append(tuple(row))
    return grouped


def _operation_with_cells(conn, operation_id: str, account_id: str) -> tuple[tuple[Any, ...], list[tuple[Any, ...]]] | None:
    row = conn.execute(
        f"SELECT {OPERATION_SELECT} FROM web_storyboard_grid_operations WHERE id=? AND account_id=?",
        (operation_id, account_id),
    ).fetchone()
    if not row:
        return None
    operation = tuple(row)
    cells = _cells_for_operations(conn, [operation_id]).get(operation_id, [])
    return operation, cells


def _check_replay(
    operation: tuple[Any, ...],
    *,
    stored_fingerprint: str,
    source_asset_id: str,
    spec: dict[str, int | float],
) -> bool:
    if str(operation[2]) != source_asset_id:
        return False
    try:
        stored_spec = _spec_from_operation(operation)
        source_bytes = int(operation[8])
    except (TypeError, ValueError):
        return False
    source_sha256 = str(operation[7] or "")
    if re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None or source_bytes < 1 or stored_spec != spec:
        return False
    expected = _request_fingerprint(
        source_asset_id=source_asset_id,
        source_sha256=source_sha256,
        source_bytes=source_bytes,
        spec=spec,
    )
    return hmac.compare_digest(str(stored_fingerprint or ""), expected)


def _source_row_for_account(conn, *, source_asset_id: str, account_id: str):
    return conn.execute(
        """SELECT id, project_id, extension, content_type, byte_size, sha256, storage_key, state
           FROM web_asset_files WHERE id=? AND account_id=?""",
        (source_asset_id, account_id),
    ).fetchone()


def _safe_output_details(operation: tuple[Any, ...], cells: list[tuple[Any, ...]]) -> tuple[Path, bytes]:
    storage_key = str(operation[17] or "")
    expected_bytes = int(operation[20] or 0)
    expected_digest = str(operation[21] or "")
    if not storage_key or expected_bytes < 1 or re.fullmatch(r"[0-9a-f]{64}", expected_digest) is None:
        raise StoryboardGridError("ZIP Storyboard Grid không còn integrity", code="STORYBOARD_GRID_OUTPUT_INVALID")
    expected = _expected_cells_from_rows(cells)
    if len(expected) != int(operation[16]):
        raise StoryboardGridError("Metadata cảnh Storyboard Grid không còn hợp lệ", code="STORYBOARD_GRID_OUTPUT_INVALID")
    return _output_path(_feature_root(), storage_key), _manifest_for_operation(operation, cells)


def reconcile_storyboard_grid_storage(*, interrupted_before: str | None = None) -> None:
    """Fail closed for interrupted grid requests and orphaned private archives."""
    if not storyboard_grid_enabled():
        return
    ensure_copyfast_schema()
    root = _feature_root()
    outputs = _private_directory(root, "outputs")
    staging = _private_directory(root, ".staging")
    now = utc_now()
    interrupted_cutoff = ""
    if interrupted_before is not None:
        try:
            parsed = datetime.fromisoformat(str(interrupted_before).strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuntimeError("Startup Storyboard Grid reconciliation fence không hợp lệ") from exc
        if parsed.tzinfo is None:
            raise RuntimeError("Startup Storyboard Grid reconciliation fence phải có timezone")
        interrupted_cutoff = parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
    with transaction() as conn:
        sql = """SELECT id FROM web_storyboard_grid_operations
                 WHERE state IN ('queued', 'processing')"""
        params: tuple[str, ...] = ()
        if interrupted_cutoff:
            sql += " AND COALESCE(started_at, queued_at, created_at, updated_at) < ?"
            params = (interrupted_cutoff,)
        interrupted = conn.execute(sql, params).fetchall()
        for row in interrupted:
            operation_id = str(row[0])
            conn.execute(
                """UPDATE web_storyboard_grid_operations
                   SET state='failed', failure_code='STORYBOARD_GRID_INTERRUPTED', updated_at=?
                   WHERE id=? AND state IN ('queued', 'processing')""",
                (now, operation_id),
            )
            _record_event(conn, operation_id=operation_id, state="failed", when=now)
        operation_rows = conn.execute(
            f"""SELECT {OPERATION_SELECT} FROM web_storyboard_grid_operations
                WHERE state='completed'"""
        ).fetchall()
        operations = [tuple(row) for row in operation_rows]
        cells_by_operation = _cells_for_operations(conn, [str(operation[0]) for operation in operations])
    known_storage: set[str] = set()
    for operation in operations:
        operation_id = str(operation[0])
        account_id = str(operation[1])
        cells = cells_by_operation.get(operation_id, [])
        path: Path | None = None
        valid = False
        try:
            path, manifest = _safe_output_details(operation, cells)
            _verify_archive_path(
                path,
                expected_bytes=int(operation[20]),
                expected_digest=str(operation[21]),
                expected_cells=_expected_cells_from_rows(cells),
                expected_manifest=manifest,
            )
            known_storage.add(str(operation[17]))
            valid = True
        except (StoryboardGridError, OSError, RuntimeError):
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


@router.get("")
async def list_storyboard_grids(
    limit: int = 20,
    offset: int = Query(0, ge=0, le=10_000),
    account: dict = Depends(require_account),
):
    _require_enabled()
    bounded_limit = max(1, min(int(limit), 50))
    ensure_copyfast_schema()
    account_id = str(account["id"])
    with transaction() as conn:
        rows = conn.execute(
            f"""SELECT {OPERATION_SELECT} FROM web_storyboard_grid_operations
                WHERE account_id=? ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (account_id, bounded_limit + 1, int(offset)),
        ).fetchall()
        operations = [tuple(row) for row in rows[:bounded_limit]]
        cells_by_operation = _cells_for_operations(conn, [str(operation[0]) for operation in operations])
    has_more = len(rows) > bounded_limit
    public_operations = [
        _public_operation(operation, cells_by_operation.get(str(operation[0]), []))
        for operation in operations
    ]
    return envelope(
        True,
        "Đã tải Storyboard Grid riêng tư.",
        data={
            "items": public_operations,
            "pagination": {
                "offset": int(offset),
                "returned": len(public_operations),
                "has_more": has_more,
                "next_offset": int(offset) + bounded_limit if has_more else None,
                "previous_offset": max(0, int(offset) - bounded_limit) if int(offset) > 0 else None,
            },
        },
        status_name="completed",
    )


@router.post("")
async def create_storyboard_grid(
    payload: StoryboardGridRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Split one verified private Asset Vault image into a private ZIP.

    This is intentionally a bounded synchronous Web-native transform.  It
    accepts neither raw browser bytes nor file paths/URLs, does not alter the
    selected source asset, and never invokes the Bot, a provider, PayOS, Xu
    wallet, job queue, notification adapter or browser canvas.
    """

    _require_enabled()
    ensure_copyfast_schema()
    root = _feature_root()
    account_id = str(account["id"])
    source_asset_id = str(payload.source_asset_id)
    spec = _normalized_spec(payload)
    operation_id = ""
    source_copy: Path | None = None
    final_path: Path | None = None
    capacity_reserved = False
    source_project_id: str | None = None
    source_extension = ""
    source_storage_key = ""
    source_bytes = 0
    source_sha256 = ""
    source_width = 0
    source_height = 0

    try:
        with transaction() as conn:
            # An immutable completed/failed operation must replay before a
            # live source lookup.  Owners may retrieve their original result
            # even after archiving its source Asset Vault image.
            existing = conn.execute(
                f"""SELECT {OPERATION_SELECT} FROM web_storyboard_grid_operations
                    WHERE account_id=? AND idempotency_key=?""",
                (account_id, payload.idempotency_key),
            ).fetchone()
            if existing:
                existing_operation = tuple(existing)
                if _check_replay(
                    existing_operation,
                    stored_fingerprint=str(existing_operation[6] or ""),
                    source_asset_id=source_asset_id,
                    spec=spec,
                ):
                    existing_cells = _cells_for_operations(conn, [str(existing_operation[0])]).get(str(existing_operation[0]), [])
                    return _operation_response(_public_operation(existing_operation, existing_cells))
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho Storyboard Grid khác")

            source_row = _source_row_for_account(conn, source_asset_id=source_asset_id, account_id=account_id)
            if not _asset_source_is_valid(source_row):
                return _source_not_found()
            assert source_row is not None
            source_project_id = str(source_row[1]) if source_row[1] else None
            source_extension = str(source_row[2]).lower()
            source_bytes = int(source_row[4])
            source_sha256 = str(source_row[5])
            source_storage_key = str(source_row[6])

            # One slot covers verified decode + all crop encodes.  A prior
            # idempotent request exits before this resource is reserved.
            capacity = image_decoder_capacity()
            if not capacity.acquire(blocking=False):
                raise HTTPException(
                    status_code=429,
                    detail="Storyboard Grid đang bận xử lý một ảnh khác; vui lòng thử lại sau ít phút",
                )
            capacity_reserved = True

        source_copy = _staging_path(root, f".source{source_extension}")
        await run_in_threadpool(
            _copy_verified_source,
            source_copy,
            storage_key=source_storage_key,
            expected_bytes=source_bytes,
            expected_digest=source_sha256,
        )
        source_width, source_height = await run_in_threadpool(_inspect_geometry, source_copy, extension=source_extension)
        # Apply the Bot's grid maths before an operation row exists, so an
        # impossible geometry can never appear as a successful Web operation.
        await run_in_threadpool(
            _grid_cells_for_geometry,
            source_width=source_width,
            source_height=source_height,
            spec=spec,
        )

        with transaction() as conn:
            # Recheck after the isolated descriptor-verified copy.  The
            # source must remain the same active immutable asset before an
            # operation can acquire a visible state.
            existing = conn.execute(
                f"""SELECT {OPERATION_SELECT} FROM web_storyboard_grid_operations
                    WHERE account_id=? AND idempotency_key=?""",
                (account_id, payload.idempotency_key),
            ).fetchone()
            if existing:
                existing_operation = tuple(existing)
                if _check_replay(
                    existing_operation,
                    stored_fingerprint=str(existing_operation[6] or ""),
                    source_asset_id=source_asset_id,
                    spec=spec,
                ):
                    existing_cells = _cells_for_operations(conn, [str(existing_operation[0])]).get(str(existing_operation[0]), [])
                    return _operation_response(_public_operation(existing_operation, existing_cells))
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho Storyboard Grid khác")

            current_source = _source_row_for_account(conn, source_asset_id=source_asset_id, account_id=account_id)
            if (
                not _asset_source_is_valid(current_source)
                or current_source is None
                or int(current_source[4]) != source_bytes
                or not hmac.compare_digest(str(current_source[5]), source_sha256)
                or not hmac.compare_digest(str(current_source[6]), source_storage_key)
            ):
                return _source_not_found()

            request_fingerprint = _request_fingerprint(
                source_asset_id=source_asset_id,
                source_sha256=source_sha256,
                source_bytes=source_bytes,
                spec=spec,
            )
            operation_id = str(uuid.uuid4())
            now = utc_now()
            conn.execute(
                """INSERT INTO web_storyboard_grid_operations
                   (id, account_id, source_asset_id, project_id, state, idempotency_key,
                    request_fingerprint, source_sha256, source_byte_size, source_width,
                    source_height, rows, cols, episode, start_scene, trim_percent,
                    scene_count, created_at, queued_at, started_at, updated_at)
                   VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    operation_id,
                    account_id,
                    source_asset_id,
                    source_project_id,
                    payload.idempotency_key,
                    request_fingerprint,
                    source_sha256,
                    source_bytes,
                    source_width,
                    source_height,
                    int(spec["rows"]),
                    int(spec["cols"]),
                    int(spec["episode"]),
                    int(spec["start_scene"]),
                    float(spec["trim_percent"]),
                    int(spec["scene_count"]),
                    now,
                    now,
                    now,
                    now,
                ),
            )
            _record_event(conn, operation_id=operation_id, state="queued", when=now)
            conn.execute(
                """UPDATE web_storyboard_grid_operations
                   SET state='processing', updated_at=?
                   WHERE id=? AND account_id=? AND state='queued'""",
                (now, operation_id, account_id),
            )
            _record_event(conn, operation_id=operation_id, state="processing", when=now)

        final_path, output_storage_key, output_bytes, output_digest, rendered_cells = await run_in_threadpool(
            _render_grid_archive,
            root,
            source_copy,
            extension=source_extension,
            source_width=source_width,
            source_height=source_height,
            spec=spec,
        )

        now = utc_now()
        with transaction() as conn:
            current = conn.execute(
                "SELECT state FROM web_storyboard_grid_operations WHERE id=? AND account_id=?",
                (operation_id, account_id),
            ).fetchone()
            if not current or str(current[0]) != "processing":
                raise RuntimeError("Storyboard Grid không còn ở trạng thái có thể hoàn tất")
            if not _quota_available(conn, account_id=account_id, additional_bytes=output_bytes):
                raise HTTPException(status_code=413, detail="Storyboard Grid đã đạt quota lưu trữ của Web account")
            if len(rendered_cells) != int(spec["scene_count"]):
                raise RuntimeError("Storyboard Grid không có đủ metadata cảnh để hoàn tất")
            for rendered in rendered_cells:
                conn.execute(
                    """INSERT INTO web_storyboard_grid_cells
                       (id, operation_id, scene_no, row_index, column_index, crop_x, crop_y,
                        width, height, original_filename, byte_size, sha256)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid.uuid4()),
                        operation_id,
                        int(rendered["scene_no"]),
                        int(rendered["row_index"]),
                        int(rendered["column_index"]),
                        int(rendered["crop_x"]),
                        int(rendered["crop_y"]),
                        int(rendered["width"]),
                        int(rendered["height"]),
                        str(rendered["original_filename"]),
                        int(rendered["byte_size"]),
                        str(rendered["sha256"]),
                    ),
                )
            conn.execute(
                """UPDATE web_storyboard_grid_operations
                   SET state='completed', storage_key=?, original_filename=?, content_type=?,
                       byte_size=?, sha256=?, completed_at=?, updated_at=?, failure_code=NULL
                   WHERE id=? AND account_id=? AND state='processing'""",
                (
                    output_storage_key,
                    ZIP_FILENAME,
                    ZIP_MEDIA_TYPE,
                    output_bytes,
                    output_digest,
                    now,
                    now,
                    operation_id,
                    account_id,
                ),
            )
            _record_event(conn, operation_id=operation_id, state="completed", when=now)
            _record_audit(
                conn,
                account_id=account_id,
                canonical_user_id=None,
                action="web.storyboard_grid.created",
                request_id=_request_id(request),
                target=operation_id,
                detail=(
                    f"source={source_width}x{source_height};grid={int(spec['rows'])}x{int(spec['cols'])};"
                    f"episode={int(spec['episode'])};start_scene={int(spec['start_scene'])};"
                    f"trim={float(spec['trim_percent']):.6f};cells={int(spec['scene_count'])};bytes={output_bytes}"
                ),
            )
            completed = _operation_with_cells(conn, operation_id, account_id)
        if completed is None:
            raise RuntimeError("Không thể đọc Storyboard Grid vừa hoàn tất")
        final_path = None
        return _operation_response(_public_operation(completed[0], completed[1]))
    except StoryboardGridError as exc:
        _safe_unlink(final_path)
        if exc.code == "STORYBOARD_GRID_SOURCE_UNAVAILABLE":
            _mark_source_unavailable(source_asset_id, account_id)
        _mark_failed(operation_id, account_id, request=request, code=exc.code)
        raise HTTPException(status_code=_error_status(exc.code), detail=exc.public_message) from exc
    except HTTPException as exc:
        _safe_unlink(final_path)
        _mark_failed(
            operation_id,
            account_id,
            request=request,
            code="STORYBOARD_GRID_QUOTA" if exc.status_code == 413 else "STORYBOARD_GRID_REQUEST",
        )
        raise
    except Exception as exc:
        _safe_unlink(final_path)
        _mark_failed(operation_id, account_id, request=request, code="STORYBOARD_GRID_OPERATION")
        raise HTTPException(status_code=500, detail="Không thể tách Storyboard Grid an toàn") from exc
    finally:
        _safe_unlink(source_copy)
        if capacity_reserved:
            image_decoder_capacity().release()


def _read_verified_cell(
    stream,
    *,
    cell: dict[str, Any],
) -> bytes:
    """Read exactly one already-authenticated JPEG member from a verified ZIP."""

    parser_stream = _parser_copy(stream)
    try:
        expected_name = str(cell["original_filename"])
        with ZipFile(parser_stream, "r") as archive:
            info = archive.getinfo(expected_name)
            if info.is_dir() or info.file_size < 1 or info.file_size > _maximum_output_bytes():
                raise StoryboardGridError("JPEG cảnh storyboard không còn integrity", code="STORYBOARD_GRID_OUTPUT_INVALID")
            payload = archive.read(info)
        byte_size, digest = _verify_jpeg_bytes(
            payload,
            expected_width=int(cell["width"]),
            expected_height=int(cell["height"]),
        )
        if byte_size != int(cell["byte_size"]) or not hmac.compare_digest(digest, str(cell["sha256"])):
            raise StoryboardGridError("JPEG cảnh storyboard không còn integrity", code="STORYBOARD_GRID_OUTPUT_INVALID")
        return payload
    except StoryboardGridError:
        raise
    except (BadZipFile, KeyError, OSError, RuntimeError, ValueError) as exc:
        raise StoryboardGridError("JPEG cảnh storyboard không còn integrity", code="STORYBOARD_GRID_OUTPUT_INVALID") from exc
    finally:
        parser_stream.close()
        stream.seek(0)


def _completed_archive_for_owner(operation_id: str, account_id: str) -> tuple[tuple[Any, ...], list[tuple[Any, ...]]] | None:
    ensure_copyfast_schema()
    with transaction() as conn:
        result = _operation_with_cells(conn, operation_id, account_id)
    if result is None or str(result[0][4]) != "completed":
        return None
    return result


@router.get("/{operation_id}/cells/{cell_id}/download")
async def download_storyboard_grid_cell(
    operation_id: str,
    cell_id: str,
    account: dict = Depends(require_account),
):
    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã Storyboard Grid")
    cell_id = _uuid(cell_id, label="Mã cảnh Storyboard Grid")
    account_id = str(account["id"])
    result = _completed_archive_for_owner(operation_id, account_id)
    if result is None:
        return _operation_not_found()
    operation, rows = result
    matching = next((row for row in rows if str(row[0]) == cell_id), None)
    if matching is None:
        return _operation_not_found()
    private_path: Path | None = None
    verified_stream = None
    try:
        private_path, manifest = _safe_output_details(operation, rows)
        expected_cells = _expected_cells_from_rows(rows)
        selected = _expected_cells_from_rows([matching])[0]
        verified_stream = _open_verified_archive_stream(
            private_path,
            expected_bytes=int(operation[20]),
            expected_digest=str(operation[21]),
            expected_cells=expected_cells,
            expected_manifest=manifest,
        )
        payload = _read_verified_cell(verified_stream, cell=selected)
    except (StoryboardGridError, OSError, RuntimeError):
        _mark_output_unavailable(operation_id, account_id)
        _safe_unlink(private_path)
        return _operation_unavailable()
    finally:
        if verified_stream is not None:
            verified_stream.close()
    return Response(
        content=payload,
        media_type=JPEG_MEDIA_TYPE,
        headers={
            "Content-Length": str(len(payload)),
            "Content-Disposition": f'attachment; filename="{str(selected["original_filename"])}"',
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.get("/{operation_id}/download")
async def download_storyboard_grid(operation_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã Storyboard Grid")
    account_id = str(account["id"])
    result = _completed_archive_for_owner(operation_id, account_id)
    if result is None:
        return _operation_not_found()
    operation, rows = result
    private_path: Path | None = None
    try:
        if str(operation[19] or "") != ZIP_MEDIA_TYPE:
            raise RuntimeError("Artifact Storyboard Grid có MIME không hợp lệ")
        private_path, manifest = _safe_output_details(operation, rows)
        verified_stream = _open_verified_archive_stream(
            private_path,
            expected_bytes=int(operation[20]),
            expected_digest=str(operation[21]),
            expected_cells=_expected_cells_from_rows(rows),
            expected_manifest=manifest,
        )
    except (StoryboardGridError, OSError, RuntimeError):
        _mark_output_unavailable(operation_id, account_id)
        _safe_unlink(private_path)
        return _operation_unavailable()
    return StreamingResponse(
        _stream_open_file(verified_stream),
        media_type=ZIP_MEDIA_TYPE,
        background=BackgroundTask(verified_stream.close),
        headers={
            "Content-Length": str(int(operation[20])),
            "Content-Disposition": f'attachment; filename="{ZIP_FILENAME}"',
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.get("/{operation_id}")
async def get_storyboard_grid(operation_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã Storyboard Grid")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with transaction() as conn:
        result = _operation_with_cells(conn, operation_id, account_id)
        events = conn.execute(
            """SELECT state, created_at FROM web_storyboard_grid_events
               WHERE operation_id=? ORDER BY sequence ASC, id ASC LIMIT 60""",
            (operation_id,),
        ).fetchall()
    if result is None:
        return _operation_not_found()
    operation, cells = result
    state = str(operation[4])
    return envelope(
        True,
        "Đã tải trạng thái Storyboard Grid riêng tư.",
        data={
            "operation": _public_operation(operation, cells),
            "events": [{"state": str(event[0]), "created_at": str(event[1])} for event in events],
        },
        status_name=state if state in STATE_VALUES else "guarded",
    )
