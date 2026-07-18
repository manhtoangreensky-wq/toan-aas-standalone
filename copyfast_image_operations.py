"""Bounded, private Web-native image operations.

Resize & Aspect Studio and Image Enhance Studio mirror bounded deterministic
local Telegram image helpers.  They deliberately improve the transport
boundary for the Web: inputs are owner-scoped Asset Vault blobs, bytes are
hash-copied into isolated staging, and only a verified fresh PNG is made
downloadable.  This module never calls the Bot, a provider, PayOS, a Xu
ledger, a webhook, or browser-supplied paths.
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

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from copyfast_auth import _record_audit, _request_id, envelope, require_account, require_csrf
from copyfast_db import (
    asset_vault_directory,
    asset_vault_enabled,
    ensure_copyfast_schema,
    image_operations_directory,
    image_operations_enabled,
    image_brand_overlay_enabled,
    image_enhance_enabled,
    image_resize_enabled,
    transaction,
    utc_now,
)
from copyfast_image_runtime import image_decoder_capacity


router = APIRouter(prefix="/api/v1/image-operations", tags=["Web Image Operations"])

IMAGE_RESIZE_KIND = "image_resize"
IMAGE_ENHANCE_KIND = "image_enhance"
IMAGE_BRAND_OVERLAY_KIND = "image_brand_overlay"
SUPPORTED_KINDS = frozenset({IMAGE_RESIZE_KIND, IMAGE_ENHANCE_KIND, IMAGE_BRAND_OVERLAY_KIND})
# An omitted kind is the combined history contract used by `/image/history`.
# Keep it explicit rather than treating every present/future table value as a
# public Web history row. New operation kinds require a deliberate UI/API
# contract change before they can appear in this projection.
IMAGE_HISTORY_KINDS = frozenset({IMAGE_RESIZE_KIND, IMAGE_ENHANCE_KIND})
OPERATION_STATES = frozenset({"queued", "processing", "completed", "failed", "unavailable", "guarded"})
FIT_MODES = frozenset({"crop", "pad", "blur"})
ENHANCE_FIT_MODE = "enhance"
BRAND_OVERLAY_FIT_MODE = "brand_overlay"
BRAND_OVERLAY_PRESET = "brand_overlay_v1"
BRAND_OVERLAY_RENDERER_VERSION = "brand_overlay_v1"
ENHANCE_TONES = frozenset({"neutral", "warm", "cool", "clean"})
OVERLAY_POSITIONS = frozenset({
    "top_left", "top_center", "top_right",
    "center_left", "center", "center_right",
    "bottom_left", "bottom_center", "bottom_right",
})
LOGO_SCALE_PERCENTAGES = frozenset({12, 18, 22})
DEFAULT_LOGO_SCALE_PERCENT = 18
DEFAULT_LOGO_OPACITY_PERCENT = 78
MIN_LOGO_OPACITY_PERCENT = 25
MAX_LOGO_OPACITY_PERCENT = 100
IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{12,160}$")
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.IGNORECASE)
ASSET_STORAGE_KEY_PATTERN = re.compile(r"^objects/[0-9a-f]{32}\.blob$")
OUTPUT_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.png$")
CHUNK_BYTES = 1024 * 1024

# Asset Vault normally limits uploads to 20 MiB.  Repeat the smaller bound at
# this execution boundary so an old or manually inserted asset cannot make a
# decoder process a larger byte stream.
MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS_PER_SOURCE = 16 * 1024 * 1024
MAX_IMAGE_DIMENSION = 7_680
MAX_IMAGE_ASPECT_RATIO = 12
MIN_TARGET_DIMENSION = 128
MAX_TARGET_DIMENSION = 4_096
MAX_OUTPUT_PIXELS = 16 * 1024 * 1024
MAX_OUTPUT_ASPECT_RATIO = 12
ORPHAN_RETENTION_SECONDS = 60 * 60

# The bot’s historical local resize presets, expressed as canonical Web
# intent.  Custom dimensions are bounded independently and never silently
# fall back to 1:1 when a request is malformed.
RESIZE_PRESETS: dict[str, tuple[int, int]] = {
    "1:1": (1024, 1024),
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "4:5": (1080, 1350),
    "3:4": (1080, 1440),
    "4:3": (1440, 1080),
    "3:2": (1500, 1000),
    "2:3": (1000, 1500),
    "21:9": (1920, 823),
}
PRESET_ALIASES = {
    "custom": "custom",
    "1:1": "1:1",
    "1x1": "1:1",
    "square": "1:1",
    "vuong": "1:1",
    "9:16": "9:16",
    "9x16": "9:16",
    "vertical": "9:16",
    "doc": "9:16",
    "reels": "9:16",
    "tiktok": "9:16",
    "16:9": "16:9",
    "16x9": "16:9",
    "horizontal": "16:9",
    "ngang": "16:9",
    "youtube": "16:9",
    "4:5": "4:5",
    "4x5": "4:5",
    "3:4": "3:4",
    "3x4": "3:4",
    "4:3": "4:3",
    "4x3": "4:3",
    "3:2": "3:2",
    "3x2": "3:2",
    "2:3": "2:3",
    "2x3": "2:3",
    "21:9": "21:9",
    "21x9": "21:9",
}
IMAGE_INPUT_MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
PNG_MEDIA_TYPE = "image/png"
OUTPUT_FILENAME = "toan-aas-image-resized.png"
ENHANCE_OUTPUT_FILENAME = "toan-aas-image-enhanced.png"
BRAND_OVERLAY_OUTPUT_FILENAME = "toan-aas-image-brand-overlay.png"

# Values and visual treatment intentionally match the Bot's local image editor
# baseline.  The Web uses the stricter Image Operations source/output limits
# and never labels this deterministic renderer as AI editing or AI upscale.
ENHANCE_PRESETS: dict[str, dict[str, float | str]] = {
    "photo_clear_detail": {"brightness": 1.03, "contrast": 1.10, "saturation": 1.05, "sharpness": 1.30, "tone": "neutral"},
    "product_clean": {"brightness": 1.08, "contrast": 1.08, "saturation": 1.02, "sharpness": 1.22, "tone": "clean"},
    "cinematic_warm": {"brightness": 0.99, "contrast": 1.14, "saturation": 1.08, "sharpness": 1.12, "tone": "warm"},
    "fresh_blue": {"brightness": 1.03, "contrast": 1.08, "saturation": 1.12, "sharpness": 1.16, "tone": "cool"},
    "food_vivid": {"brightness": 1.04, "contrast": 1.12, "saturation": 1.24, "sharpness": 1.25, "tone": "warm"},
}
ENHANCE_ADJUSTMENT_KEYS = ("brightness", "contrast", "saturation", "sharpness")

OPERATION_SELECT = """id, source_asset_id, project_id, kind, state, target_width, target_height,
                       preset, fit_mode, source_width, source_height, original_filename, content_type,
                       byte_size, created_at, queued_at, started_at, completed_at, updated_at,
                        failure_code, storage_key, sha256, source_byte_size, source_sha256, settings_json"""


class ImageOperationError(Exception):
    """Known safe error that must not disclose a decoder or storage trace."""

    def __init__(self, message: str, *, code: str = "IMAGE_OPERATION_INVALID"):
        super().__init__(message)
        self.public_message = message
        self.code = code


class ImageResizeRequest(BaseModel):
    """One immutable Asset Vault image becomes one fresh private PNG."""

    source_asset_id: str = Field(min_length=36, max_length=36)
    preset: str = Field(default="custom", min_length=1, max_length=24)
    target_width: int | None = Field(default=None, ge=MIN_TARGET_DIMENSION, le=MAX_TARGET_DIMENSION)
    target_height: int | None = Field(default=None, ge=MIN_TARGET_DIMENSION, le=MAX_TARGET_DIMENSION)
    fit_mode: str = Field(default="pad", min_length=3, max_length=12)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("source_asset_id")
    @classmethod
    def valid_source_asset_id(cls, value: str) -> str:
        return _uuid(value, label="Asset Vault ID")

    @field_validator("preset")
    @classmethod
    def valid_preset(cls, value: str) -> str:
        candidate = str(value or "").strip().lower().replace("×", "x")
        if candidate not in PRESET_ALIASES:
            raise ValueError("Preset Resize & Aspect không hợp lệ")
        return PRESET_ALIASES[candidate]

    @field_validator("fit_mode")
    @classmethod
    def valid_fit_mode(cls, value: str) -> str:
        candidate = str(value or "").strip().lower()
        if candidate not in FIT_MODES:
            raise ValueError("Chế độ khung chỉ nhận crop, pad hoặc blur")
        return candidate

    @field_validator("idempotency_key")
    @classmethod
    def valid_idempotency_key(cls, value: str) -> str:
        return _idempotency_key(value)


class ImageEnhanceRequest(BaseModel):
    """One immutable Asset Vault image becomes a deterministic local PNG."""

    source_asset_id: str = Field(min_length=36, max_length=36)
    preset: str = Field(default="photo_clear_detail", min_length=1, max_length=40)
    brightness: float | None = Field(default=None, ge=0.5, le=2.0)
    contrast: float | None = Field(default=None, ge=0.5, le=2.0)
    saturation: float | None = Field(default=None, ge=0.5, le=2.0)
    sharpness: float | None = Field(default=None, ge=0.5, le=2.0)
    tone: str | None = Field(default=None, min_length=1, max_length=16)
    basic_upscale: bool = False
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("source_asset_id")
    @classmethod
    def valid_source_asset_id(cls, value: str) -> str:
        return _uuid(value, label="Asset Vault ID")

    @field_validator("preset")
    @classmethod
    def valid_preset(cls, value: str) -> str:
        candidate = str(value or "").strip().lower()
        if candidate not in {*ENHANCE_PRESETS, "custom"}:
            raise ValueError("Preset Image Enhance không hợp lệ")
        return candidate

    @field_validator(*ENHANCE_ADJUSTMENT_KEYS)
    @classmethod
    def valid_adjustment(cls, value: float | None) -> float | None:
        if value is None:
            return None
        candidate = float(value)
        if not math.isfinite(candidate) or candidate < 0.5 or candidate > 2.0:
            raise ValueError("Thông số chỉnh ảnh phải từ 0.50 đến 2.00")
        return candidate

    @field_validator("tone")
    @classmethod
    def valid_tone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        candidate = str(value or "").strip().lower()
        if candidate not in ENHANCE_TONES:
            raise ValueError("Tone chỉ nhận neutral, warm, cool hoặc clean")
        return candidate

    @field_validator("idempotency_key")
    @classmethod
    def valid_idempotency_key(cls, value: str) -> str:
        return _idempotency_key(value)


class ImageBrandOverlayRequest(BaseModel):
    """Create a private branded copy from one source and an optional logo asset.

    Text is intentionally plain text only.  The browser never supplies markup,
    font paths, image bytes, URLs or arbitrary composition coordinates.
    """

    source_asset_id: str = Field(min_length=36, max_length=36)
    overlay_text: str | None = Field(default=None, max_length=520)
    text_position: str = Field(default="bottom_center", min_length=3, max_length=24)
    logo_asset_id: str | None = Field(default=None, min_length=36, max_length=36)
    logo_position: str = Field(default="bottom_right", min_length=3, max_length=24)
    logo_scale_percent: int = Field(default=DEFAULT_LOGO_SCALE_PERCENT, ge=12, le=22)
    logo_opacity_percent: int = Field(default=DEFAULT_LOGO_OPACITY_PERCENT, ge=MIN_LOGO_OPACITY_PERCENT, le=MAX_LOGO_OPACITY_PERCENT)
    idempotency_key: str = Field(min_length=12, max_length=160)

    @field_validator("source_asset_id")
    @classmethod
    def valid_source_asset_id(cls, value: str) -> str:
        return _uuid(value, label="Asset Vault ID")

    @field_validator("logo_asset_id")
    @classmethod
    def valid_logo_asset_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _uuid(value, label="Logo Asset Vault ID")

    @field_validator("overlay_text")
    @classmethod
    def valid_overlay_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = re.sub(r"\s+", " ", str(value).strip())
        if not normalized:
            return None
        if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
            raise ValueError("Chữ thương hiệu không được chứa ký tự điều khiển")
        if len(normalized) > 260:
            raise ValueError("Chữ thương hiệu tối đa 260 ký tự")
        return normalized

    @field_validator("text_position", "logo_position")
    @classmethod
    def valid_overlay_position(cls, value: str) -> str:
        normalized = re.sub(r"[\s-]+", "_", str(value or "").strip().lower())
        if normalized not in OVERLAY_POSITIONS:
            raise ValueError("Vị trí overlay không hợp lệ")
        return normalized

    @field_validator("logo_scale_percent")
    @classmethod
    def valid_logo_scale_percent(cls, value: int) -> int:
        normalized = int(value)
        if normalized not in LOGO_SCALE_PERCENTAGES:
            raise ValueError("Kích thước logo chỉ nhận 12, 18 hoặc 22 phần trăm")
        return normalized

    @field_validator("idempotency_key")
    @classmethod
    def valid_idempotency_key(cls, value: str) -> str:
        return _idempotency_key(value)


def _require_enabled() -> None:
    if not image_operations_enabled() or not asset_vault_enabled():
        raise HTTPException(
            status_code=503,
            detail="Image Operations cần Asset Vault private và storage đầu ra riêng đã được bật",
        )


def _require_resize_enabled() -> None:
    _require_enabled()
    if not image_resize_enabled():
        raise HTTPException(
            status_code=503,
            detail="Resize & Aspect Studio chưa được bật; cần WEBAPP_IMAGE_RESIZE_ENABLED và private storage",
        )


def _require_enhance_enabled() -> None:
    _require_enabled()
    if not image_enhance_enabled():
        raise HTTPException(
            status_code=503,
            detail="Image Enhance Studio chưa được bật; cần WEBAPP_IMAGE_ENHANCE_ENABLED và private storage",
        )


def _require_brand_overlay_enabled() -> None:
    _require_enabled()
    if not image_brand_overlay_enabled():
        raise HTTPException(
            status_code=503,
            detail="Brand Overlay Studio chưa được bật; cần WEBAPP_IMAGE_BRAND_OVERLAY_ENABLED và private storage",
        )


def ensure_image_operations_runtime() -> None:
    """Fail closed when an enabled private image root lacks Pillow runtime."""
    if not image_operations_enabled():
        return
    _image_classes()


def _image_classes():
    try:
        from PIL import Image, ImageFile, ImageFilter, ImageOps, UnidentifiedImageError
    except ImportError as exc:  # pragma: no cover - deployment configuration
        raise ImageOperationError(
            "Resize & Aspect Studio chưa có runtime Pillow an toàn",
            code="IMAGE_RUNTIME_UNAVAILABLE",
        ) from exc
    # A partial image must never be treated as a valid private source or
    # artifact.  Reassert this in case another module changed Pillow globals.
    ImageFile.LOAD_TRUNCATED_IMAGES = False
    return Image, ImageFile, ImageFilter, ImageOps, UnidentifiedImageError


def _maximum_output_bytes() -> int:
    raw = os.environ.get("WEBAPP_IMAGE_OPERATIONS_MAX_OUTPUT_MB", "20").strip()
    try:
        megabytes = int(raw)
    except ValueError:
        megabytes = 20
    return max(1, min(megabytes, 50)) * 1024 * 1024


def _maximum_account_bytes() -> int:
    raw = os.environ.get("WEBAPP_IMAGE_OPERATIONS_QUOTA_MB", "100").strip()
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


def _asset_path(root: Path, storage_key: str) -> Path:
    if not ASSET_STORAGE_KEY_PATTERN.fullmatch(storage_key):
        raise RuntimeError("Storage key Asset Vault không hợp lệ")
    candidate = (root / storage_key).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError("Storage key Asset Vault vượt ngoài thư mục riêng") from exc
    return candidate


def _output_path(root: Path, storage_key: str) -> Path:
    if not OUTPUT_STORAGE_KEY_PATTERN.fullmatch(storage_key):
        raise RuntimeError("Storage key Image Operation không hợp lệ")
    candidate = (root / storage_key).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError("Storage key Image Operation vượt ngoài storage riêng") from exc
    return candidate


def _private_operation_directory(root: Path, name: str) -> Path:
    if name not in {".staging", "outputs"}:
        raise RuntimeError("Thư mục Image Operation không hợp lệ")
    private_root = root.resolve()
    candidate = private_root / name
    if candidate.exists() and candidate.is_symlink():
        raise RuntimeError("Thư mục Image Operation không được là symbolic link")
    candidate.mkdir(parents=True, exist_ok=True)
    if not candidate.is_dir() or candidate.is_symlink():
        raise RuntimeError("Thư mục Image Operation không hợp lệ")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise RuntimeError("Thư mục Image Operation vượt ngoài storage riêng") from exc
    return resolved


def _staging_path(root: Path, suffix: str) -> Path:
    return _private_operation_directory(root, ".staging") / f"{uuid.uuid4().hex}{suffix}"


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


def _image_magic_matches(extension: str, prefix: bytes) -> bool:
    if extension in {".jpg", ".jpeg"}:
        return prefix.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return prefix.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".webp":
        return len(prefix) >= 12 and prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP"
    return False


def _copy_verified_image_source(
    source: Path,
    destination: Path,
    *,
    extension: str,
    expected_bytes: int,
    expected_digest: str,
) -> None:
    """Make an integrity-checked isolated copy before Pillow sees source bytes."""
    total = 0
    digest = hashlib.sha256()
    prefix = b""
    try:
        if not source.is_file() or source.is_symlink() or source.stat().st_size != expected_bytes:
            raise ImageOperationError("Ảnh nguồn không còn sẵn sàng", code="IMAGE_SOURCE_UNAVAILABLE")
    except ImageOperationError:
        raise
    except OSError as exc:
        raise ImageOperationError("Không thể đọc ảnh nguồn riêng tư", code="IMAGE_SOURCE_UNAVAILABLE") from exc
    try:
        with source.open("rb") as read_stream:
            try:
                with destination.open("xb") as write_stream:
                    while True:
                        try:
                            chunk = read_stream.read(CHUNK_BYTES)
                        except OSError as exc:
                            raise ImageOperationError("Không thể đọc ảnh nguồn riêng tư", code="IMAGE_SOURCE_UNAVAILABLE") from exc
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_INPUT_BYTES:
                            raise ImageOperationError("Ảnh nguồn vượt giới hạn 20 MB", code="IMAGE_INPUT_TOO_LARGE")
                        if len(prefix) < 16:
                            prefix += chunk[: 16 - len(prefix)]
                        digest.update(chunk)
                        try:
                            write_stream.write(chunk)
                        except OSError as exc:
                            raise ImageOperationError(
                                "Không thể chuẩn bị vùng xử lý ảnh riêng tư",
                                code="IMAGE_STAGING_UNAVAILABLE",
                            ) from exc
            except ImageOperationError:
                raise
            except OSError as exc:
                # Destination open/close failures belong to the isolated
                # staging boundary. They must never poison a valid source
                # Asset Vault record as unavailable.
                raise ImageOperationError(
                    "Không thể chuẩn bị vùng xử lý ảnh riêng tư",
                    code="IMAGE_STAGING_UNAVAILABLE",
                ) from exc
    except ImageOperationError:
        _safe_unlink(destination)
        raise
    except OSError as exc:
        _safe_unlink(destination)
        raise ImageOperationError("Không thể đọc ảnh nguồn riêng tư", code="IMAGE_SOURCE_UNAVAILABLE") from exc
    if (
        total != expected_bytes
        or not hmac.compare_digest(digest.hexdigest(), expected_digest)
        or not _image_magic_matches(extension, prefix)
    ):
        raise ImageOperationError("Ảnh nguồn không vượt qua kiểm tra integrity", code="IMAGE_SOURCE_UNAVAILABLE")


def _image_format_matches(extension: str, image_format: str | None) -> bool:
    expected = {
        ".jpg": {"JPEG"},
        ".jpeg": {"JPEG"},
        ".png": {"PNG"},
        ".webp": {"WEBP"},
    }.get(extension, set())
    return str(image_format or "").upper() in expected


def _validate_dimensions(width: int, height: int, *, source: bool) -> None:
    label = "nguồn" if source else "đầu ra"
    max_dimension = MAX_IMAGE_DIMENSION if source else MAX_TARGET_DIMENSION
    max_pixels = MAX_IMAGE_PIXELS_PER_SOURCE if source else MAX_OUTPUT_PIXELS
    max_aspect = MAX_IMAGE_ASPECT_RATIO if source else MAX_OUTPUT_ASPECT_RATIO
    if width < 1 or height < 1:
        raise ImageOperationError(f"Kích thước ảnh {label} không hợp lệ", code="IMAGE_DIMENSION_LIMIT")
    if width > max_dimension or height > max_dimension:
        raise ImageOperationError(
            f"Cạnh dài ảnh {label} vượt giới hạn {max_dimension} px",
            code="IMAGE_DIMENSION_LIMIT",
        )
    if width * height > max_pixels:
        raise ImageOperationError(
            f"Độ phân giải ảnh {label} vượt giới hạn xử lý an toàn",
            code="IMAGE_PIXEL_LIMIT",
        )
    if max(width, height) / min(width, height) > max_aspect:
        raise ImageOperationError(
            f"Tỷ lệ khung hình ảnh {label} vượt giới hạn xử lý an toàn",
            code="IMAGE_ASPECT_RATIO_LIMIT",
        )


def _inspect_image_source(source_copy: Path, *, extension: str) -> tuple[int, int]:
    """Validate headers and compressed bytes before a full decode occurs."""
    Image, ImageFile, _, _, UnidentifiedImageError = _image_classes()
    if ImageFile.LOAD_TRUNCATED_IMAGES:
        raise ImageOperationError("Image runtime không ở chế độ kiểm tra đầy đủ", code="IMAGE_RUNTIME_UNAVAILABLE")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source_copy) as verifier:
                if not _image_format_matches(extension, verifier.format):
                    raise ImageOperationError("Định dạng ảnh nguồn không khớp Asset Vault", code="IMAGE_SOURCE_INVALID")
                if int(getattr(verifier, "n_frames", 1) or 1) != 1 or bool(getattr(verifier, "is_animated", False)):
                    raise ImageOperationError("Ảnh động chưa được hỗ trợ trong Resize Studio", code="IMAGE_ANIMATED")
                width, height = (int(verifier.size[0]), int(verifier.size[1]))
                _validate_dimensions(width, height, source=True)
                # verify() validates compressed source structure without
                # retaining a decoded raster in memory.
                verifier.verify()
        return width, height
    except ImageOperationError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ImageOperationError(
            "Độ phân giải ảnh nguồn vượt giới hạn xử lý an toàn",
            code="IMAGE_PIXEL_LIMIT",
        ) from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageOperationError("Ảnh không hợp lệ hoặc bị hỏng", code="IMAGE_PARSE_FAILED") from exc


def _normalized_spec(payload: ImageResizeRequest) -> tuple[str, int, int, str]:
    """Resolve bot parity presets and reject conflicting client geometry."""
    preset = str(payload.preset)
    if preset == "custom":
        if payload.target_width is None or payload.target_height is None:
            raise HTTPException(status_code=422, detail="Preset Tùy chỉnh cần chiều rộng và chiều cao từ 128 đến 4096 px")
        width, height = int(payload.target_width), int(payload.target_height)
    else:
        width, height = RESIZE_PRESETS[preset]
        if payload.target_width is not None and int(payload.target_width) != width:
            raise HTTPException(status_code=422, detail="Chiều rộng không khớp preset Aspect đã chọn")
        if payload.target_height is not None and int(payload.target_height) != height:
            raise HTTPException(status_code=422, detail="Chiều cao không khớp preset Aspect đã chọn")
    try:
        _validate_dimensions(width, height, source=False)
    except ImageOperationError as exc:
        raise HTTPException(status_code=413, detail=exc.public_message) from exc
    return preset, width, height, str(payload.fit_mode)


def _normalized_enhance_spec(payload: ImageEnhanceRequest) -> tuple[str, dict[str, float | str | bool]]:
    """Resolve Bot-parity presets without accepting ambiguous client overrides."""
    preset = str(payload.preset)
    supplied_adjustments = {key: getattr(payload, key) for key in ENHANCE_ADJUSTMENT_KEYS}
    if preset == "custom":
        missing = [key for key, value in supplied_adjustments.items() if value is None]
        if missing:
            raise HTTPException(status_code=422, detail="Tùy chỉnh Image Enhance cần đủ sáng, tương phản, bão hòa và độ nét")
        config: dict[str, float | str | bool] = {
            key: round(float(value), 4) for key, value in supplied_adjustments.items() if value is not None
        }
        config["tone"] = str(payload.tone or "neutral")
    else:
        if any(value is not None for value in supplied_adjustments.values()) or payload.tone is not None:
            raise HTTPException(status_code=422, detail="Preset Image Enhance không nhận thông số tùy chỉnh kèm theo")
        config = dict(ENHANCE_PRESETS[preset])
    config["basic_upscale"] = bool(payload.basic_upscale)
    return preset, config


def _normalized_brand_overlay_spec(payload: ImageBrandOverlayRequest) -> dict[str, str | int | None]:
    """Remove irrelevant controls so one logical composition has one fingerprint."""
    overlay_text = payload.overlay_text
    logo_asset_id = payload.logo_asset_id
    if not overlay_text and not logo_asset_id:
        raise HTTPException(status_code=422, detail="Brand Overlay cần ít nhất chữ thương hiệu hoặc logo private")
    if logo_asset_id and logo_asset_id == payload.source_asset_id:
        raise HTTPException(status_code=422, detail="Logo phải là Asset Vault image khác với ảnh nguồn")
    return {
        "overlay_text": overlay_text,
        "text_position": payload.text_position if overlay_text else "bottom_center",
        "logo_asset_id": logo_asset_id,
        "logo_position": payload.logo_position if logo_asset_id else "bottom_right",
        "logo_scale_percent": int(payload.logo_scale_percent) if logo_asset_id else DEFAULT_LOGO_SCALE_PERCENT,
        "logo_opacity_percent": int(payload.logo_opacity_percent) if logo_asset_id else DEFAULT_LOGO_OPACITY_PERCENT,
    }


def _request_fingerprint(
    *,
    source_asset_id: str,
    source_sha256: str,
    source_bytes: int,
    preset: str,
    target_width: int,
    target_height: int,
    fit_mode: str,
) -> str:
    encoded = json.dumps(
        {
            "kind": IMAGE_RESIZE_KIND,
            "source_asset_id": source_asset_id,
            "source_sha256": source_sha256,
            "source_bytes": source_bytes,
            "preset": preset,
            "target_width": target_width,
            "target_height": target_height,
            "fit_mode": fit_mode,
            "output_format": "png",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _enhance_request_fingerprint(
    *,
    source_asset_id: str,
    source_sha256: str,
    source_bytes: int,
    preset: str,
    settings: dict[str, float | str | bool],
) -> str:
    encoded = json.dumps(
        {
            "kind": IMAGE_ENHANCE_KIND,
            "source_asset_id": source_asset_id,
            "source_sha256": source_sha256,
            "source_bytes": source_bytes,
            "preset": preset,
            "settings": settings,
            "output_format": "png",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _brand_overlay_text_digest(value: str | None) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _brand_overlay_request_fingerprint(
    *,
    source_asset_id: str,
    source_sha256: str,
    source_bytes: int,
    logo_asset_id: str | None,
    logo_sha256: str | None,
    logo_bytes: int,
    overlay_text: str | None,
    text_position: str,
    logo_position: str,
    logo_scale_percent: int,
    logo_opacity_percent: int,
) -> str:
    """Bind every rendering input without persisting branded text in a row.

    The normalized text itself stays in the request lifecycle only.  The
    stored request fingerprint and settings carry its SHA-256 digest so an
    idempotency replay remains deterministic even after its source/logo asset
    has later been archived.
    """
    encoded = json.dumps(
        {
            "kind": IMAGE_BRAND_OVERLAY_KIND,
            "renderer_version": BRAND_OVERLAY_RENDERER_VERSION,
            "source_asset_id": source_asset_id,
            "source_sha256": source_sha256,
            "source_bytes": source_bytes,
            "logo_asset_id": logo_asset_id or "",
            "logo_sha256": logo_sha256 or "",
            "logo_bytes": logo_bytes,
            "overlay_text_digest": _brand_overlay_text_digest(overlay_text),
            "text_position": text_position,
            "logo_position": logo_position,
            "logo_scale_percent": logo_scale_percent,
            "logo_opacity_percent": logo_opacity_percent,
            "output_format": "png",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _brand_overlay_storage_settings(
    *,
    overlay_text: str | None,
    text_position: str,
    logo_asset_id: str | None,
    logo_sha256: str | None,
    logo_bytes: int,
    logo_position: str,
    logo_scale_percent: int,
    logo_opacity_percent: int,
) -> dict[str, str | int | bool]:
    """Store replay-only metadata; public operation views get an allow-list."""
    return {
        "renderer_version": BRAND_OVERLAY_RENDERER_VERSION,
        "text_present": bool(overlay_text),
        "text_digest": _brand_overlay_text_digest(overlay_text),
        "text_position": text_position,
        "logo_present": bool(logo_asset_id),
        "logo_asset_id": logo_asset_id or "",
        "logo_sha256": logo_sha256 or "",
        "logo_byte_size": int(logo_bytes),
        "logo_position": logo_position,
        "logo_scale_percent": int(logo_scale_percent),
        "logo_opacity_percent": int(logo_opacity_percent),
    }


def _brand_overlay_internal_settings(value: Any) -> dict[str, Any]:
    try:
        decoded = json.loads(str(value or "{}"))
    except (TypeError, ValueError):
        return {}
    if not isinstance(decoded, dict):
        return {}
    return decoded


def _brand_overlay_settings_are_valid(settings: dict[str, Any]) -> bool:
    """Validate stored replay metadata without trusting arbitrary old JSON."""
    try:
        logo_scale_percent = int(settings.get("logo_scale_percent") or 0)
        logo_opacity_percent = int(settings.get("logo_opacity_percent") or 0)
        logo_byte_size = int(settings.get("logo_byte_size") or 0)
    except (TypeError, ValueError):
        return False
    return (
        str(settings.get("renderer_version") or "") == BRAND_OVERLAY_RENDERER_VERSION
        and isinstance(settings.get("text_present"), bool)
        and isinstance(settings.get("logo_present"), bool)
        and isinstance(settings.get("text_digest"), str)
        and re.fullmatch(r"[0-9a-f]{64}", str(settings.get("text_digest") or "")) is not None
        and str(settings.get("text_position") or "") in OVERLAY_POSITIONS
        and str(settings.get("logo_position") or "") in OVERLAY_POSITIONS
        and logo_scale_percent in LOGO_SCALE_PERCENTAGES
        and MIN_LOGO_OPACITY_PERCENT <= logo_opacity_percent <= MAX_LOGO_OPACITY_PERCENT
        and (not bool(settings.get("logo_present")) or (
            UUID_PATTERN.fullmatch(str(settings.get("logo_asset_id") or "")) is not None
            and re.fullmatch(r"[0-9a-f]{64}", str(settings.get("logo_sha256") or "")) is not None
            and logo_byte_size > 0
        ))
    )


def _brand_overlay_replay_matches(
    operation: tuple[Any, ...],
    stored_fingerprint: Any,
    *,
    source_asset_id: str,
    overlay_text: str | None,
    text_position: str,
    logo_asset_id: str | None,
    logo_position: str,
    logo_scale_percent: int,
    logo_opacity_percent: int,
) -> bool:
    """Check a replay from persisted immutable fingerprints, not live assets."""
    if len(operation) <= 24 or str(operation[1] or "") != source_asset_id:
        return False
    source_sha256 = str(operation[23] or "")
    source_bytes = int(operation[22] or 0)
    if re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None or source_bytes < 1:
        return False
    settings = _brand_overlay_internal_settings(operation[24])
    if not _brand_overlay_settings_are_valid(settings):
        return False
    text_present = bool(settings["text_present"])
    logo_present = bool(settings["logo_present"])
    if text_present != bool(overlay_text) or logo_present != bool(logo_asset_id):
        return False
    if text_present and not hmac.compare_digest(str(settings["text_digest"]), _brand_overlay_text_digest(overlay_text)):
        return False
    if logo_present and not hmac.compare_digest(str(settings["logo_asset_id"]), str(logo_asset_id or "")):
        return False
    expected = _brand_overlay_request_fingerprint(
        source_asset_id=source_asset_id,
        source_sha256=source_sha256,
        source_bytes=source_bytes,
        logo_asset_id=str(settings["logo_asset_id"]) if logo_present else None,
        logo_sha256=str(settings["logo_sha256"]) if logo_present else None,
        logo_bytes=int(settings["logo_byte_size"]) if logo_present else 0,
        overlay_text=overlay_text,
        text_position=text_position,
        logo_position=logo_position,
        logo_scale_percent=logo_scale_percent,
        logo_opacity_percent=logo_opacity_percent,
    )
    return hmac.compare_digest(str(stored_fingerprint or ""), expected)


def _operation_settings(kind: str, value: Any) -> dict[str, Any]:
    """Expose only server-normalized settings, never arbitrary stored JSON."""
    decoded = _brand_overlay_internal_settings(value)
    if kind == IMAGE_BRAND_OVERLAY_KIND:
        if not _brand_overlay_settings_are_valid(decoded):
            return {}
        return {
            "text_present": bool(decoded["text_present"]),
            "text_position": str(decoded["text_position"]),
            "logo_present": bool(decoded["logo_present"]),
            "logo_position": str(decoded["logo_position"]),
            "logo_scale_percent": int(decoded["logo_scale_percent"]),
            "logo_opacity_percent": int(decoded["logo_opacity_percent"]),
        }
    settings: dict[str, Any] = {}
    for key in ENHANCE_ADJUSTMENT_KEYS:
        candidate = decoded.get(key)
        if isinstance(candidate, (int, float)) and not isinstance(candidate, bool) and math.isfinite(float(candidate)) and 0.5 <= float(candidate) <= 2.0:
            settings[key] = round(float(candidate), 4)
    tone = decoded.get("tone")
    if isinstance(tone, str) and tone in ENHANCE_TONES:
        settings["tone"] = tone
    if isinstance(decoded.get("basic_upscale"), bool):
        settings["basic_upscale"] = decoded["basic_upscale"]
    return settings


def _operation_output_filename(kind: str) -> str:
    if kind == IMAGE_ENHANCE_KIND:
        return ENHANCE_OUTPUT_FILENAME
    if kind == IMAGE_BRAND_OVERLAY_KIND:
        return BRAND_OVERLAY_OUTPUT_FILENAME
    return OUTPUT_FILENAME


def _operation_public(row: tuple[Any, ...]) -> dict[str, Any]:
    state = str(row[4])
    byte_size = int(row[13]) if row[13] is not None else None
    return {
        "id": str(row[0]),
        "source_asset_id": str(row[1]),
        "project_id": str(row[2]) if row[2] else None,
        "kind": str(row[3]),
        "state": state,
        "target_width": int(row[5]),
        "target_height": int(row[6]),
        "preset": str(row[7]),
        "fit_mode": str(row[8]),
        "source_width": int(row[9]) if row[9] is not None else None,
        "source_height": int(row[10]) if row[10] is not None else None,
        "original_filename": str(row[11]) if row[11] else None,
        "content_type": str(row[12]) if row[12] else None,
        "byte_size": byte_size,
        "created_at": str(row[14]),
        "queued_at": str(row[15]),
        "started_at": str(row[16]) if row[16] else None,
        "completed_at": str(row[17]) if row[17] else None,
        "updated_at": str(row[18]),
        "download_ready": state == "completed" and bool(row[20]) and byte_size is not None,
        "settings": _operation_settings(str(row[3]), row[24] if len(row) > 24 else "{}"),
    }


def _operation_response(operation: dict[str, Any]) -> dict[str, Any]:
    state = str(operation.get("state") or "failed")
    kind = str(operation.get("kind") or "")
    is_enhance = kind == IMAGE_ENHANCE_KIND
    is_brand_overlay = kind == IMAGE_BRAND_OVERLAY_KIND
    label = "Brand Overlay Studio" if is_brand_overlay else ("Image Enhance Studio" if is_enhance else "Resize & Aspect Studio")
    if state == "completed":
        message = (
            "Đã ghép lớp thương hiệu và xác minh PNG riêng tư."
            if is_brand_overlay
            else ("Đã nâng chất lượng cơ bản và xác minh PNG riêng tư." if is_enhance else "Đã resize và xác minh PNG riêng tư.")
        )
        return envelope(True, message, data={"operation": operation}, status_name="completed")
    if state in {"queued", "processing"}:
        return envelope(True, f"{label} đang được máy chủ xử lý.", data={"operation": operation}, status_name=state)
    if state == "guarded":
        return envelope(False, f"{label} đã được chặn an toàn; không có output thay thế.", data={"operation": operation}, status_name="guarded", error_code="WEB_IMAGE_OPERATION_GUARDED")
    return envelope(False, f"{label} không hoàn tất; không có output được phát hành.", data={"operation": operation}, status_name=state, error_code="WEB_IMAGE_OPERATION_FAILED")


def _operation_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy thao tác ảnh thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_IMAGE_OPERATION_NOT_FOUND",
    )


def _source_not_found(kind: str = IMAGE_RESIZE_KIND) -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy ảnh private đang hoạt động thuộc Web account hiện tại.",
        status_name="guarded",
        error_code=(
            "WEB_IMAGE_BRAND_OVERLAY_SOURCE_NOT_FOUND"
            if kind == IMAGE_BRAND_OVERLAY_KIND
            else ("WEB_IMAGE_ENHANCE_SOURCE_NOT_FOUND" if kind == IMAGE_ENHANCE_KIND else "WEB_IMAGE_RESIZE_SOURCE_NOT_FOUND")
        ),
    )


def _logo_not_found() -> dict[str, Any]:
    return envelope(
        False,
        "Không tìm thấy logo private đang hoạt động thuộc Web account hiện tại.",
        status_name="guarded",
        error_code="WEB_IMAGE_BRAND_OVERLAY_LOGO_NOT_FOUND",
    )


def _operation_unavailable() -> dict[str, Any]:
    return envelope(
        False,
        "PNG đầu ra không còn sẵn sàng để tải. Hãy tạo bản sao mới hoặc liên hệ hỗ trợ.",
        status_name="guarded",
        error_code="WEB_IMAGE_OPERATION_UNAVAILABLE",
    )


def _image_operation_error_status(code: str) -> int:
    """Map known safe processing failures to a truthful public HTTP class."""
    if code in {
        "IMAGE_INPUT_TOO_LARGE",
        "IMAGE_DIMENSION_LIMIT",
        "IMAGE_ASPECT_RATIO_LIMIT",
        "IMAGE_PIXEL_LIMIT",
        "IMAGE_OUTPUT_LIMIT",
    }:
        return 413
    if code in {"IMAGE_RUNTIME_UNAVAILABLE", "IMAGE_STAGING_UNAVAILABLE", "IMAGE_OVERLAY_FONT_UNAVAILABLE"}:
        # Runtime/storage boundary failures are retriable service conditions,
        # not invalid user input and never evidence against its source.
        return 503
    return 422


def _record_event(conn, *, operation_id: str, state: str, when: str | None = None) -> None:
    if state not in OPERATION_STATES:
        raise RuntimeError("Trạng thái Image Operation không hợp lệ")
    row = conn.execute(
        "SELECT COALESCE(MAX(sequence), 0) + 1 FROM web_image_operation_events WHERE operation_id=?",
        (operation_id,),
    ).fetchone()
    sequence = int(row[0] or 1) if row else 1
    conn.execute(
        """INSERT INTO web_image_operation_events (id, operation_id, state, sequence, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), operation_id, state, sequence, when or utc_now()),
    )


def _quota_available(conn, *, account_id: str, additional_bytes: int) -> bool:
    row = conn.execute(
        """SELECT COALESCE(SUM(byte_size), 0)
           FROM web_image_operations
           WHERE account_id=? AND state='completed' AND byte_size IS NOT NULL""",
        (account_id,),
    ).fetchone()
    used = int(row[0] or 0) if row else 0
    return used + additional_bytes <= _maximum_account_bytes()


def _mark_failed(
    operation_id: str,
    account_id: str,
    *,
    request: Request,
    code: str,
    kind: str = IMAGE_RESIZE_KIND,
) -> None:
    if not operation_id:
        return
    if kind not in SUPPORTED_KINDS:
        return
    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            "SELECT state FROM web_image_operations WHERE id=? AND account_id=? AND kind=?",
            (operation_id, account_id, kind),
        ).fetchone()
        if not row or str(row[0]) not in {"queued", "processing"}:
            return
        conn.execute(
            """UPDATE web_image_operations
               SET state='failed', failure_code=?, updated_at=?
               WHERE id=? AND account_id=?""",
            (code[:80], now, operation_id, account_id),
        )
        _record_event(conn, operation_id=operation_id, state="failed", when=now)
        _record_audit(
            conn,
            account_id=account_id,
            canonical_user_id=None,
            action=f"web.image_operation.{kind}_failed",
            request_id=_request_id(request),
            target=operation_id,
            detail=f"code={code[:80]}",
        )


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


def _mark_output_unavailable(operation_id: str, account_id: str) -> None:
    now = utc_now()
    with transaction() as conn:
        row = conn.execute(
            "SELECT state FROM web_image_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
        if not row or str(row[0]) != "completed":
            return
        conn.execute(
            """UPDATE web_image_operations
               SET state='unavailable', failure_code='IMAGE_OUTPUT_UNAVAILABLE', updated_at=?
               WHERE id=? AND account_id=?""",
            (now, operation_id, account_id),
        )
        _record_event(conn, operation_id=operation_id, state="unavailable", when=now)


def _cover_resize(image, *, width: int, height: int, resample):
    """Centre-crop before resize, matching the local bot without a giant canvas.

    Scaling first can turn a valid thin source into a hundreds-of-megapixels
    temporary image. Cropping in source coordinates first is equivalent to the
    bot helper's deterministic centre crop, keeps intermediates bounded by the
    validated source/output sizes, and avoids a one-request memory DoS.
    """
    source_width, source_height = image.size
    if source_width * height > source_height * width:
        cropped_width = max(1, int(source_height * width / height))
        left = max(0, (source_width - cropped_width) // 2)
        crop_box = (left, 0, left + cropped_width, source_height)
    else:
        cropped_height = max(1, int(source_width * height / width))
        top = max(0, (source_height - cropped_height) // 2)
        crop_box = (0, top, source_width, top + cropped_height)
    cropped = image.crop(crop_box)
    try:
        return cropped.resize((width, height), resample=resample)
    finally:
        cropped.close()


def _contain_resize(image, *, width: int, height: int, resample):
    source_width, source_height = image.size
    scale = min(width / source_width, height / source_height)
    # The bot uses int()/floor for its local contain geometry. Keeping that
    # rounding rule makes pad/blur placement deterministic across surfaces.
    resized_width = max(1, min(width, int(source_width * scale)))
    resized_height = max(1, min(height, int(source_height * scale)))
    return image.resize((resized_width, resized_height), resample=resample)


def _render_resize(source_copy: Path, *, extension: str, target_width: int, target_height: int, fit_mode: str):
    """Render the exact deterministic crop/pad/blur modes from local bot parity."""
    Image, _, ImageFilter, ImageOps, UnidentifiedImageError = _image_classes()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            _inspect_image_source(source_copy, extension=extension)
            with Image.open(source_copy) as decoded:
                if not _image_format_matches(extension, decoded.format):
                    raise ImageOperationError("Định dạng ảnh nguồn không khớp Asset Vault", code="IMAGE_SOURCE_INVALID")
                if int(getattr(decoded, "n_frames", 1) or 1) != 1 or bool(getattr(decoded, "is_animated", False)):
                    raise ImageOperationError("Ảnh động chưa được hỗ trợ trong Resize Studio", code="IMAGE_ANIMATED")
                decoded.load()
                normalized = ImageOps.exif_transpose(decoded)
                # A fresh opaque RGB canvas removes EXIF, ICC/comment chunks,
                # alpha and source metadata. PNG remains the canonical bot
                # parity output, never a misleading "AI upscale" artifact.
                rgba = normalized.convert("RGBA")
                source_rgb = Image.new("RGB", rgba.size, (255, 255, 255))
                source_rgb.paste(rgba, mask=rgba.getchannel("A"))
                resample = Image.Resampling.LANCZOS
                if fit_mode == "crop":
                    rendered = _cover_resize(source_rgb, width=target_width, height=target_height, resample=resample)
                elif fit_mode == "pad":
                    foreground = _contain_resize(source_rgb, width=target_width, height=target_height, resample=resample)
                    try:
                        rendered = Image.new("RGB", (target_width, target_height), (255, 255, 255))
                        rendered.paste(
                            foreground,
                            ((target_width - foreground.width) // 2, (target_height - foreground.height) // 2),
                        )
                    finally:
                        foreground.close()
                elif fit_mode == "blur":
                    background = _cover_resize(source_rgb, width=target_width, height=target_height, resample=resample)
                    # Pillow always provides ImageFilter in the supported
                    # pinned runtime. If it were unavailable we fail rather
                    # than label an unblurred background as blur.
                    try:
                        if ImageFilter is None:
                            raise ImageOperationError("Runtime blur chưa sẵn sàng", code="IMAGE_RUNTIME_UNAVAILABLE")
                        rendered = background.filter(ImageFilter.GaussianBlur(radius=28))
                    finally:
                        background.close()
                    foreground = _contain_resize(source_rgb, width=target_width, height=target_height, resample=resample)
                    try:
                        rendered.paste(
                            foreground,
                            ((target_width - foreground.width) // 2, (target_height - foreground.height) // 2),
                        )
                    finally:
                        foreground.close()
                else:  # defensive; Pydantic has already normalized this.
                    raise ImageOperationError("Chế độ khung không hợp lệ", code="IMAGE_FIT_MODE_INVALID")
                if rendered.mode != "RGB" or rendered.size != (target_width, target_height):
                    raise ImageOperationError("Kết quả Resize không hợp lệ", code="IMAGE_OUTPUT_INVALID")
                return rendered
    except ImageOperationError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ImageOperationError("Độ phân giải ảnh nguồn vượt giới hạn xử lý an toàn", code="IMAGE_PIXEL_LIMIT") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageOperationError("Không thể decode ảnh nguồn an toàn", code="IMAGE_PARSE_FAILED") from exc


def _enhance_target_dimensions(
    source_width: int,
    source_height: int,
    *,
    basic_upscale: bool,
) -> tuple[int, int]:
    """Derive one bounded PNG geometry before persisting an Enhance operation.

    Asset Vault permits a larger (but bounded) source for compatibility.  The
    emitted PNG is stricter: at most 4096 px per side / 16 MP.  Large sources
    therefore downscale deterministically even when basic upscale is off;
    basic upscale otherwise requests up to 2x only within that same ceiling.
    """
    source_pixels = source_width * source_height
    ceiling = min(
        MAX_TARGET_DIMENSION / source_width,
        MAX_TARGET_DIMENSION / source_height,
        math.sqrt(MAX_OUTPUT_PIXELS / source_pixels),
    )
    if ceiling <= 0:
        raise ImageOperationError("Không thể xác định kích thước PNG đầu ra", code="IMAGE_OUTPUT_LIMIT")
    if ceiling < 1:
        scale = ceiling
    elif basic_upscale:
        candidate = min(2.0, ceiling)
        # Preserve Bot's small-change threshold: a near-identity enlargement
        # is not advertised as an upscale, but its sharpen pass still applies.
        scale = candidate if candidate > 1.02 else 1.0
    else:
        scale = 1.0
    target_width = max(1, int(source_width * scale))
    target_height = max(1, int(source_height * scale))
    _validate_dimensions(target_width, target_height, source=False)
    return target_width, target_height


def _inspect_enhance_geometry(
    source_copy: Path,
    *,
    extension: str,
    basic_upscale: bool,
) -> tuple[int, int, int, int]:
    """Read EXIF orientation and derive immutable Enhance geometry pre-insert."""
    Image, ImageFile, _, _, UnidentifiedImageError = _image_classes()
    if ImageFile.LOAD_TRUNCATED_IMAGES:
        raise ImageOperationError("Image runtime không ở chế độ kiểm tra đầy đủ", code="IMAGE_RUNTIME_UNAVAILABLE")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source_copy) as verifier:
                if not _image_format_matches(extension, verifier.format):
                    raise ImageOperationError("Định dạng ảnh nguồn không khớp Asset Vault", code="IMAGE_SOURCE_INVALID")
                if int(getattr(verifier, "n_frames", 1) or 1) != 1 or bool(getattr(verifier, "is_animated", False)):
                    raise ImageOperationError("Ảnh động chưa được hỗ trợ trong Image Enhance Studio", code="IMAGE_ANIMATED")
                width, height = (int(verifier.size[0]), int(verifier.size[1]))
                _validate_dimensions(width, height, source=True)
                try:
                    orientation = int(verifier.getexif().get(274, 1) or 1)
                except (AttributeError, TypeError, ValueError):
                    orientation = 1
                if orientation in {5, 6, 7, 8}:
                    width, height = height, width
                _validate_dimensions(width, height, source=True)
                target_width, target_height = _enhance_target_dimensions(
                    width,
                    height,
                    basic_upscale=basic_upscale,
                )
                return width, height, target_width, target_height
    except ImageOperationError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ImageOperationError("Độ phân giải ảnh nguồn vượt giới hạn xử lý an toàn", code="IMAGE_PIXEL_LIMIT") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageOperationError("Không thể đọc thông số ảnh nguồn an toàn", code="IMAGE_PARSE_FAILED") from exc


def _inspect_brand_overlay_geometry(source_copy: Path, *, extension: str) -> tuple[int, int, int, int]:
    """Reuse the bounded output geometry without exposing Enhance semantics."""
    try:
        return _inspect_enhance_geometry(source_copy, extension=extension, basic_upscale=False)
    except ImageOperationError as exc:
        if exc.code == "IMAGE_ANIMATED":
            raise ImageOperationError("Ảnh động chưa được hỗ trợ trong Brand Overlay Studio", code=exc.code) from exc
        raise


def _apply_enhance_tone(image, *, tone: str, Image):
    if tone not in {"warm", "cool", "clean"}:
        return image
    colors = {"warm": (255, 190, 120), "cool": (120, 205, 255), "clean": (255, 255, 255)}
    opacity = 0.055 if tone != "clean" else 0.035
    overlay = Image.new("RGB", image.size, colors[tone])
    try:
        return Image.blend(image, overlay, opacity)
    finally:
        overlay.close()


def _render_enhance(
    source_copy: Path,
    *,
    extension: str,
    settings: dict[str, float | str | bool],
    target_width: int,
    target_height: int,
):
    """Apply the Bot's deterministic local enhance order without AI/provider calls."""
    Image, _, ImageFilter, ImageOps, UnidentifiedImageError = _image_classes()
    try:
        from PIL import ImageEnhance
    except ImportError as exc:  # pragma: no cover - pinned Pillow deployment
        raise ImageOperationError("Image Enhance Studio chưa có runtime Pillow an toàn", code="IMAGE_RUNTIME_UNAVAILABLE") from exc
    working = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            _inspect_image_source(source_copy, extension=extension)
            with Image.open(source_copy) as decoded:
                if not _image_format_matches(extension, decoded.format):
                    raise ImageOperationError("Định dạng ảnh nguồn không khớp Asset Vault", code="IMAGE_SOURCE_INVALID")
                if int(getattr(decoded, "n_frames", 1) or 1) != 1 or bool(getattr(decoded, "is_animated", False)):
                    raise ImageOperationError("Ảnh động chưa được hỗ trợ trong Image Enhance Studio", code="IMAGE_ANIMATED")
                decoded.load()
                normalized = ImageOps.exif_transpose(decoded)
                try:
                    rgba = normalized.convert("RGBA")
                finally:
                    if normalized is not decoded:
                        normalized.close()
                try:
                    source_rgb = Image.new("RGB", rgba.size, (255, 255, 255))
                    source_rgb.paste(rgba, mask=rgba.getchannel("A"))
                finally:
                    rgba.close()
                try:
                    _validate_dimensions(source_rgb.width, source_rgb.height, source=True)
                    expected_width, expected_height = _enhance_target_dimensions(
                        source_rgb.width,
                        source_rgb.height,
                        basic_upscale=bool(settings.get("basic_upscale")),
                    )
                    if (expected_width, expected_height) != (target_width, target_height):
                        raise ImageOperationError("Kích thước Image Enhance không còn khớp yêu cầu", code="IMAGE_OUTPUT_INVALID")
                    autocontrasted = ImageOps.autocontrast(source_rgb, cutoff=1)
                    # Pillow normally returns a new image, but retain an owned
                    # copy if a future implementation returns its input. The
                    # source object is closed in this finally block.
                    working = autocontrasted.copy() if autocontrasted is source_rgb else autocontrasted
                finally:
                    source_rgb.close()
                for key, enhancer in (
                    ("brightness", ImageEnhance.Brightness),
                    ("contrast", ImageEnhance.Contrast),
                    ("saturation", ImageEnhance.Color),
                    ("sharpness", ImageEnhance.Sharpness),
                ):
                    next_image = enhancer(working).enhance(float(settings[key]))
                    working.close()
                    working = next_image
                tone_image = _apply_enhance_tone(working, tone=str(settings.get("tone") or "neutral"), Image=Image)
                if tone_image is not working:
                    working.close()
                    working = tone_image
                if working.size != (target_width, target_height):
                    resized = working.resize((target_width, target_height), resample=Image.Resampling.LANCZOS)
                    working.close()
                    working = resized
                if bool(settings.get("basic_upscale")):
                    if ImageFilter is None:
                        raise ImageOperationError("Runtime làm nét chưa sẵn sàng", code="IMAGE_RUNTIME_UNAVAILABLE")
                    sharpened = working.filter(ImageFilter.UnsharpMask(radius=1.6, percent=125, threshold=3))
                    working.close()
                    working = sharpened
                if working.mode != "RGB" or working.size != (target_width, target_height):
                    raise ImageOperationError("Kết quả Image Enhance không hợp lệ", code="IMAGE_OUTPUT_INVALID")
                rendered = working
                working = None
                return rendered
    except ImageOperationError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ImageOperationError("Độ phân giải ảnh nguồn vượt giới hạn xử lý an toàn", code="IMAGE_PIXEL_LIMIT") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageOperationError("Không thể decode ảnh cho Image Enhance an toàn", code="IMAGE_PARSE_FAILED") from exc
    finally:
        if working is not None:
            working.close()


def _overlay_image_classes():
    """Load the text compositor separately from the shared image decoder."""
    try:
        from PIL import ImageDraw, ImageFont
    except ImportError as exc:  # pragma: no cover - deployment configuration
        raise ImageOperationError(
            "Brand Overlay Studio chưa có runtime text renderer an toàn",
            code="IMAGE_OVERLAY_FONT_UNAVAILABLE",
        ) from exc
    return ImageDraw, ImageFont


def _overlay_font_paths() -> tuple[Path, ...]:
    """Return deterministic, operator-controlled font candidates.

    No browser-provided font path is ever accepted.  A production deployment
    can pin a font through ``WEBAPP_IMAGE_BRAND_OVERLAY_FONT_PATH``; otherwise
    common DejaVu locations are tried first and local Windows paths only make
    development/test behaviour deterministic. A configured path remains
    strict; otherwise the pinned Pillow runtime provides its packaged Unicode
    FreeType fallback when no host font is installed.
    """
    configured = os.environ.get("WEBAPP_IMAGE_BRAND_OVERLAY_FONT_PATH", "").strip()
    if configured:
        return (Path(configured),)
    return (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\segoeuib.ttf"),
    )


def _load_overlay_font(ImageFont, *, size: int):
    configured = os.environ.get("WEBAPP_IMAGE_BRAND_OVERLAY_FONT_PATH", "").strip()
    for candidate in _overlay_font_paths():
        try:
            if not candidate.is_file() or candidate.is_symlink():
                continue
            return ImageFont.truetype(str(candidate), size=size)
        except (OSError, ValueError):
            continue
    # A configured production path is an explicit operator assertion. Do not
    # quietly select a different face if it is absent or invalid. Without that
    # assertion, Pillow's packaged FreeType default is a deterministic Unicode
    # fallback in the pinned runtime (and avoids assuming a host font exists).
    if not configured:
        try:
            fallback = ImageFont.load_default(size=size)
            if getattr(fallback, "getbbox", None) is not None:
                return fallback
        except (OSError, TypeError, ValueError):
            pass
    raise ImageOperationError(
        "Brand Overlay Studio chưa có font Unicode được server xác nhận",
        code="IMAGE_OVERLAY_FONT_UNAVAILABLE",
    )


def _overlay_text_width(draw, value: str, *, font) -> int:
    left, _, right, _ = draw.textbbox((0, 0), value, font=font, stroke_width=1)
    return max(0, int(right) - int(left))


def _wrap_overlay_text(draw, text: str, *, font, maximum_width: int) -> list[str]:
    """Greedily wrap words without silently discarding the supplied text."""
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        if _overlay_text_width(draw, word, font=font) > maximum_width:
            raise ImageOperationError(
                "Chữ thương hiệu có từ quá dài để đặt an toàn lên ảnh",
                code="IMAGE_OVERLAY_TEXT_FIT",
            )
        candidate = word if not current else f"{current} {word}"
        if _overlay_text_width(draw, candidate, font=font) <= maximum_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines


def _fit_overlay_text(draw, text: str, *, image_width: int, image_height: int, ImageFont):
    """Choose a readable bounded font or truthfully reject non-fitting text."""
    margin = max(16, round(0.035 * min(image_width, image_height)))
    padding_x = max(18, round(0.025 * image_width))
    padding_y = max(14, round(0.018 * image_height))
    available_width = min(round(image_width * 0.82), image_width - (2 * margin) - (2 * padding_x))
    available_height = image_height - (2 * margin)
    if available_width < 24 or available_height < 32:
        raise ImageOperationError("Ảnh quá nhỏ để đặt chữ thương hiệu an toàn", code="IMAGE_OVERLAY_TEXT_FIT")
    baseline_size = max(20, min(72, image_width // 18))
    candidate_sizes = list(range(baseline_size, 15, -2))
    if 16 not in candidate_sizes:
        candidate_sizes.append(16)
    for size in candidate_sizes:
        font = _load_overlay_font(ImageFont, size=size)
        lines = _wrap_overlay_text(draw, text, font=font, maximum_width=available_width)
        line_height = max(28, round(int(getattr(font, "size", size)) * 1.25))
        if len(lines) > 4:
            continue
        block_width = max(_overlay_text_width(draw, line, font=font) for line in lines) + (2 * padding_x)
        block_height = (line_height * len(lines)) + (2 * padding_y)
        if block_width <= image_width - (2 * margin) and block_height <= available_height:
            return font, lines, block_width, block_height, line_height, margin, padding_x, padding_y
    raise ImageOperationError(
        "Chữ thương hiệu không vừa trong tối đa bốn dòng trên ảnh này",
        code="IMAGE_OVERLAY_TEXT_FIT",
    )


def _overlay_xy(
    *,
    canvas_width: int,
    canvas_height: int,
    overlay_width: int,
    overlay_height: int,
    position: str,
    margin: int,
) -> tuple[int, int]:
    if position not in OVERLAY_POSITIONS:
        raise ImageOperationError("Vị trí overlay không hợp lệ", code="IMAGE_OVERLAY_POSITION")
    if overlay_width < 1 or overlay_height < 1 or overlay_width + (2 * margin) > canvas_width or overlay_height + (2 * margin) > canvas_height:
        raise ImageOperationError("Overlay không vừa trong ảnh nguồn", code="IMAGE_OVERLAY_FIT")
    if position.startswith("top_"):
        y = margin
    elif position.startswith("bottom_"):
        y = canvas_height - overlay_height - margin
    else:
        y = (canvas_height - overlay_height) // 2
    if position.endswith("_left"):
        x = margin
    elif position.endswith("_right"):
        x = canvas_width - overlay_width - margin
    else:
        x = (canvas_width - overlay_width) // 2
    return max(margin, min(x, canvas_width - overlay_width - margin)), max(margin, min(y, canvas_height - overlay_height - margin))


def _overlay_base_canvas(source_copy: Path, *, extension: str, target_width: int, target_height: int):
    """Decode, orient and flatten the immutable source into an RGB canvas."""
    Image, _, _, ImageOps, UnidentifiedImageError = _image_classes()
    try:
        _inspect_image_source(source_copy, extension=extension)
        with Image.open(source_copy) as decoded:
            if not _image_format_matches(extension, decoded.format):
                raise ImageOperationError("Định dạng ảnh nguồn không khớp Asset Vault", code="IMAGE_SOURCE_INVALID")
            if int(getattr(decoded, "n_frames", 1) or 1) != 1 or bool(getattr(decoded, "is_animated", False)):
                raise ImageOperationError("Ảnh động chưa được hỗ trợ trong Brand Overlay Studio", code="IMAGE_ANIMATED")
            decoded.load()
            normalized = ImageOps.exif_transpose(decoded)
            try:
                rgba = normalized.convert("RGBA")
            finally:
                if normalized is not decoded:
                    normalized.close()
            try:
                source_rgb = Image.new("RGB", rgba.size, (255, 255, 255))
                source_alpha = rgba.getchannel("A")
                try:
                    source_rgb.paste(rgba, mask=source_alpha)
                finally:
                    source_alpha.close()
            finally:
                rgba.close()
        if source_rgb.size != (target_width, target_height):
            resized = source_rgb.resize((target_width, target_height), resample=Image.Resampling.LANCZOS)
            source_rgb.close()
            source_rgb = resized
        if source_rgb.mode != "RGB" or source_rgb.size != (target_width, target_height):
            source_rgb.close()
            raise ImageOperationError("Canvas Brand Overlay không hợp lệ", code="IMAGE_OUTPUT_INVALID")
        return source_rgb
    except ImageOperationError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ImageOperationError("Độ phân giải ảnh nguồn vượt giới hạn xử lý an toàn", code="IMAGE_PIXEL_LIMIT") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageOperationError("Không thể decode ảnh nguồn an toàn", code="IMAGE_PARSE_FAILED") from exc


def _overlay_logo_layer(
    logo_copy: Path,
    *,
    extension: str,
    canvas_width: int,
    canvas_height: int,
    scale_percent: int,
    opacity_percent: int,
):
    """Return one bounded transparent logo layer from its verified staging copy."""
    Image, _, _, ImageOps, UnidentifiedImageError = _image_classes()
    logo = None
    try:
        _inspect_image_source(logo_copy, extension=extension)
        with Image.open(logo_copy) as decoded:
            if not _image_format_matches(extension, decoded.format):
                raise ImageOperationError("Định dạng logo không khớp Asset Vault", code="IMAGE_LOGO_INVALID")
            if int(getattr(decoded, "n_frames", 1) or 1) != 1 or bool(getattr(decoded, "is_animated", False)):
                raise ImageOperationError("Logo động chưa được hỗ trợ", code="IMAGE_ANIMATED")
            decoded.load()
            normalized = ImageOps.exif_transpose(decoded)
            try:
                logo = normalized.convert("RGBA")
            finally:
                if normalized is not decoded:
                    normalized.close()
        margin = max(16, round(0.025 * min(canvas_width, canvas_height)))
        maximum_width = min(canvas_width - (2 * margin), max(24, round(canvas_width * scale_percent / 100)))
        maximum_height = min(canvas_height - (2 * margin), max(24, round(canvas_height * min(18, scale_percent * 0.82) / 100)))
        if maximum_width < 1 or maximum_height < 1:
            logo.close()
            raise ImageOperationError("Ảnh quá nhỏ để đặt logo an toàn", code="IMAGE_OVERLAY_FIT")
        logo.thumbnail((maximum_width, maximum_height), resample=Image.Resampling.LANCZOS)
        if logo.width < 1 or logo.height < 1:
            logo.close()
            raise ImageOperationError("Logo không có kích thước hợp lệ", code="IMAGE_LOGO_INVALID")
        alpha = logo.getchannel("A")
        try:
            adjusted_alpha = alpha.point(lambda value: max(0, min(255, round(value * opacity_percent / 100))))
        finally:
            alpha.close()
        logo.putalpha(adjusted_alpha)
        adjusted_alpha.close()
        rendered_logo = logo
        logo = None
        return rendered_logo
    except ImageOperationError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ImageOperationError("Độ phân giải logo vượt giới hạn xử lý an toàn", code="IMAGE_PIXEL_LIMIT") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageOperationError("Không thể decode logo an toàn", code="IMAGE_LOGO_INVALID") from exc
    finally:
        if logo is not None:
            logo.close()


def _render_brand_overlay(
    source_copy: Path,
    *,
    source_extension: str,
    target_width: int,
    target_height: int,
    overlay_text: str | None,
    text_position: str,
    logo_copy: Path | None,
    logo_extension: str | None,
    logo_position: str,
    logo_scale_percent: int,
    logo_opacity_percent: int,
):
    """Compose Bot-parity text first, then a private logo, into a fresh PNG."""
    Image, _, _, _, _ = _image_classes()
    ImageDraw, ImageFont = _overlay_image_classes()
    canvas = _overlay_base_canvas(
        source_copy,
        extension=source_extension,
        target_width=target_width,
        target_height=target_height,
    )
    composed = None
    try:
        composed = canvas.convert("RGBA")
        if overlay_text:
            draw = ImageDraw.Draw(composed, "RGBA")
            font, lines, block_width, block_height, line_height, margin, padding_x, padding_y = _fit_overlay_text(
                draw,
                overlay_text,
                image_width=composed.width,
                image_height=composed.height,
                ImageFont=ImageFont,
            )
            x, y = _overlay_xy(
                canvas_width=composed.width,
                canvas_height=composed.height,
                overlay_width=block_width,
                overlay_height=block_height,
                position=text_position,
                margin=margin,
            )
            radius = min(18, max(1, block_height // 2))
            draw.rounded_rectangle((x, y, x + block_width, y + block_height), radius=radius, fill=(0, 0, 0, 145))
            for index, line in enumerate(lines):
                line_width = _overlay_text_width(draw, line, font=font)
                text_x = x + ((block_width - line_width) // 2)
                text_y = y + padding_y + (index * line_height)
                draw.text(
                    (text_x, text_y),
                    line,
                    font=font,
                    fill=(255, 255, 255, 245),
                    stroke_width=1,
                    stroke_fill=(0, 0, 0, 180),
                )
        if logo_copy is not None:
            if not logo_extension:
                raise ImageOperationError("Logo không có định dạng hợp lệ", code="IMAGE_LOGO_INVALID")
            logo = _overlay_logo_layer(
                logo_copy,
                extension=logo_extension,
                canvas_width=composed.width,
                canvas_height=composed.height,
                scale_percent=logo_scale_percent,
                opacity_percent=logo_opacity_percent,
            )
            try:
                margin = max(16, round(0.025 * min(composed.width, composed.height)))
                x, y = _overlay_xy(
                    canvas_width=composed.width,
                    canvas_height=composed.height,
                    overlay_width=logo.width,
                    overlay_height=logo.height,
                    position=logo_position,
                    margin=margin,
                )
                composed.alpha_composite(logo, (x, y))
            finally:
                logo.close()
        rendered = Image.new("RGB", composed.size, (255, 255, 255))
        output_alpha = composed.getchannel("A")
        try:
            rendered.paste(composed, mask=output_alpha)
        finally:
            output_alpha.close()
        if rendered.size != (target_width, target_height):
            rendered.close()
            raise ImageOperationError("Kết quả Brand Overlay không hợp lệ", code="IMAGE_OUTPUT_INVALID")
        return rendered
    finally:
        canvas.close()
        if composed is not None:
            composed.close()


def _build_brand_overlay_output(
    root: Path,
    source_copy: Path,
    *,
    source_extension: str,
    target_width: int,
    target_height: int,
    overlay_text: str | None,
    text_position: str,
    logo_copy: Path | None,
    logo_extension: str | None,
    logo_position: str,
    logo_scale_percent: int,
    logo_opacity_percent: int,
) -> tuple[Path, str, int, str, int, int]:
    rendered = _render_brand_overlay(
        source_copy,
        source_extension=source_extension,
        target_width=target_width,
        target_height=target_height,
        overlay_text=overlay_text,
        text_position=text_position,
        logo_copy=logo_copy,
        logo_extension=logo_extension,
        logo_position=logo_position,
        logo_scale_percent=logo_scale_percent,
        logo_opacity_percent=logo_opacity_percent,
    )
    final_path, storage_key, output_bytes, output_digest = _publish_verified_png(
        root,
        rendered,
        target_width=target_width,
        target_height=target_height,
    )
    return final_path, storage_key, output_bytes, output_digest, target_width, target_height


def _parser_copy(stream):
    """Give Pillow an owned stream without allowing it to close the delivery fd."""
    try:
        stream.seek(0)
        return os.fdopen(os.dup(stream.fileno()), "rb", closefd=True)
    except (AttributeError, OSError):
        # Tests and future callers can pass a memory stream. Keep the same
        # ownership rule even when no OS descriptor exists.
        stream.seek(0)
        payload = stream.read()
        stream.seek(0)
        return BytesIO(payload)


def _verify_png_stream(stream, *, expected_width: int, expected_height: int) -> None:
    """Validate a PNG through the exact already-open file handle."""
    Image, ImageFile, _, _, UnidentifiedImageError = _image_classes()
    try:
        if ImageFile.LOAD_TRUNCATED_IMAGES:
            raise ImageOperationError("Image runtime không ở chế độ kiểm tra đầy đủ", code="IMAGE_RUNTIME_UNAVAILABLE")
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            verifier_stream = _parser_copy(stream)
            try:
                with Image.open(verifier_stream) as verifier:
                    # Pillow's PNG verifier requires this to be its first parser
                    # action. Metadata/geometry are inspected only after
                    # reopening through a second owned parser stream.
                    verifier.verify()
            finally:
                verifier_stream.close()
            stream.seek(0)
            decoded_stream = _parser_copy(stream)
            try:
                with Image.open(decoded_stream) as decoded:
                    if str(decoded.format or "").upper() != "PNG":
                        raise ImageOperationError("Định dạng PNG đầu ra không hợp lệ", code="IMAGE_OUTPUT_INVALID")
                    if int(getattr(decoded, "n_frames", 1) or 1) != 1 or bool(getattr(decoded, "is_animated", False)):
                        raise ImageOperationError("PNG đầu ra không hợp lệ", code="IMAGE_OUTPUT_INVALID")
                    if tuple(decoded.size) != (expected_width, expected_height):
                        raise ImageOperationError("Kích thước PNG đầu ra không khớp yêu cầu", code="IMAGE_OUTPUT_INVALID")
                    if decoded.getexif():
                        raise ImageOperationError("PNG đầu ra mang metadata không được phép", code="IMAGE_OUTPUT_INVALID")
                    decoded.load()
            finally:
                decoded_stream.close()
            stream.seek(0)
    except ImageOperationError:
        raise
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ImageOperationError("PNG đầu ra vượt giới hạn xử lý an toàn", code="IMAGE_OUTPUT_LIMIT") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageOperationError("PNG đầu ra không vượt qua kiểm tra", code="IMAGE_OUTPUT_INVALID") from exc


def _digest_open_stream(stream) -> str:
    digest = hashlib.sha256()
    stream.seek(0)
    while True:
        chunk = stream.read(CHUNK_BYTES)
        if not chunk:
            break
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest()


def _verify_output_png(path: Path, *, expected_width: int, expected_height: int) -> tuple[int, str]:
    """Strictly re-open the generated artifact before it can become completed."""
    try:
        if not path.is_file() or path.is_symlink():
            raise ImageOperationError("PNG đầu ra không còn sẵn sàng", code="IMAGE_OUTPUT_INVALID")
        byte_size = int(path.stat().st_size)
        if byte_size < 1 or byte_size > _maximum_output_bytes():
            raise ImageOperationError("PNG đầu ra vượt giới hạn lưu trữ", code="IMAGE_OUTPUT_LIMIT")
        with path.open("rb") as stream:
            _verify_png_stream(stream, expected_width=expected_width, expected_height=expected_height)
            digest = _digest_open_stream(stream)
        return byte_size, digest
    except ImageOperationError:
        raise
    except OSError as exc:
        raise ImageOperationError("PNG đầu ra không vượt qua kiểm tra", code="IMAGE_OUTPUT_INVALID") from exc


def _open_verified_output_stream(
    path: Path,
    *,
    expected_bytes: int,
    expected_digest: str,
    expected_width: int,
    expected_height: int,
):
    """Return the verified open descriptor that will be streamed to the owner.

    The file is hashed and parsed through this descriptor before it is exposed.
    On Linux we additionally reject symlinks at open time, so a later rename
    cannot swap the verified object for a different pathname.
    """
    flags = os.O_RDONLY | int(getattr(os, "O_NOFOLLOW", 0))
    stream = None
    try:
        stream = os.fdopen(os.open(path, flags), "rb", closefd=True)
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or int(metadata.st_size) != expected_bytes:
            raise ImageOperationError("PNG đầu ra không còn integrity", code="IMAGE_OUTPUT_INVALID")
        if expected_bytes < 1 or expected_bytes > _maximum_output_bytes():
            raise ImageOperationError("PNG đầu ra vượt giới hạn lưu trữ", code="IMAGE_OUTPUT_LIMIT")
        if not hmac.compare_digest(_digest_open_stream(stream), expected_digest):
            raise ImageOperationError("PNG đầu ra không còn integrity", code="IMAGE_OUTPUT_INVALID")
        _verify_png_stream(stream, expected_width=expected_width, expected_height=expected_height)
        return stream
    except ImageOperationError:
        if stream is not None:
            stream.close()
        raise
    except OSError as exc:
        if stream is not None:
            stream.close()
        raise ImageOperationError("PNG đầu ra không vượt qua kiểm tra", code="IMAGE_OUTPUT_INVALID") from exc


def _stream_open_file(stream):
    try:
        while True:
            chunk = stream.read(CHUNK_BYTES)
            if not chunk:
                break
            yield chunk
    finally:
        stream.close()


def _publish_verified_png(
    root: Path,
    rendered,
    *,
    target_width: int,
    target_height: int,
) -> tuple[Path, str, int, str]:
    """Save, hash, parse and atomically publish one private rendered PNG."""
    temporary_output = _staging_path(root, ".output.png")
    final_path: Path | None = None
    try:
        if getattr(rendered, "mode", "") != "RGB" or tuple(getattr(rendered, "size", ())) != (target_width, target_height):
            raise ImageOperationError("Kết quả PNG không khớp contract đầu ra", code="IMAGE_OUTPUT_INVALID")
        try:
            with temporary_output.open("xb") as stream:
                rendered.save(stream, format="PNG", optimize=True)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            rendered.close()
        output_bytes, output_digest = _verify_output_png(
            temporary_output,
            expected_width=target_width,
            expected_height=target_height,
        )
        storage_key = f"outputs/{uuid.uuid4().hex}.png"
        final_path = _output_path(root, storage_key)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        if final_path.exists() or final_path.is_symlink():
            raise ImageOperationError("Không thể chuẩn bị PNG đầu ra riêng tư", code="IMAGE_OUTPUT_INVALID")
        os.replace(temporary_output, final_path)
        if not _verify_file(final_path, expected_bytes=output_bytes, expected_digest=output_digest):
            raise ImageOperationError("PNG đầu ra không vượt qua kiểm tra integrity", code="IMAGE_OUTPUT_INVALID")
        verified_bytes, verified_digest = _verify_output_png(
            final_path,
            expected_width=target_width,
            expected_height=target_height,
        )
        if verified_bytes != output_bytes or not hmac.compare_digest(verified_digest, output_digest):
            raise ImageOperationError("PNG đầu ra không vượt qua kiểm tra integrity", code="IMAGE_OUTPUT_INVALID")
        return final_path, storage_key, output_bytes, output_digest
    except Exception:
        _safe_unlink(final_path)
        raise
    finally:
        _safe_unlink(temporary_output)


def _build_resize_output(
    root: Path,
    source_copy: Path,
    *,
    extension: str,
    target_width: int,
    target_height: int,
    fit_mode: str,
) -> tuple[Path, str, int, str, int, int]:
    """Render, atomically publish and rehash one fresh private Resize PNG."""
    _validate_dimensions(target_width, target_height, source=False)
    rendered = _render_resize(
        source_copy,
        extension=extension,
        target_width=target_width,
        target_height=target_height,
        fit_mode=fit_mode,
    )
    final_path, storage_key, output_bytes, output_digest = _publish_verified_png(
        root,
        rendered,
        target_width=target_width,
        target_height=target_height,
    )
    return final_path, storage_key, output_bytes, output_digest, target_width, target_height


def _build_enhance_output(
    root: Path,
    source_copy: Path,
    *,
    extension: str,
    settings: dict[str, float | str | bool],
    target_width: int,
    target_height: int,
) -> tuple[Path, str, int, str, int, int]:
    """Render and publish the deterministic local Image Enhance PNG."""
    _validate_dimensions(target_width, target_height, source=False)
    rendered = _render_enhance(
        source_copy,
        extension=extension,
        settings=settings,
        target_width=target_width,
        target_height=target_height,
    )
    final_path, storage_key, output_bytes, output_digest = _publish_verified_png(
        root,
        rendered,
        target_width=target_width,
        target_height=target_height,
    )
    return final_path, storage_key, output_bytes, output_digest, target_width, target_height


def reconcile_image_operation_storage(*, interrupted_before: str | None = None) -> None:
    """Fail closed for interrupted work, retained artifacts and old orphan files.

    ``interrupted_before`` is an internal startup fence captured before the
    ASGI app begins serving.  Deferred reconciliation can otherwise reach
    this module after a new synchronous render has entered ``processing`` and
    falsely mark it as leftover work from a previous process.  The strict
    comparison deliberately leaves a one-second grace window because database
    lifecycle timestamps are stored at second precision; protecting live work
    is safer than eagerly failing a just-pre-startup row.
    """
    if not image_operations_enabled():
        return
    ensure_copyfast_schema()
    root = image_operations_directory()
    outputs = _private_operation_directory(root, "outputs")
    staging = _private_operation_directory(root, ".staging")
    now = utc_now()
    interrupted_cutoff = ""
    if interrupted_before is not None:
        try:
            parsed_cutoff = datetime.fromisoformat(str(interrupted_before).strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuntimeError("Startup Image Operation reconciliation fence không hợp lệ") from exc
        if parsed_cutoff.tzinfo is None:
            raise RuntimeError("Startup Image Operation reconciliation fence phải có timezone")
        interrupted_cutoff = parsed_cutoff.astimezone(timezone.utc).isoformat(timespec="seconds")
    with transaction() as conn:
        # This feature performs work in-request and has no background worker
        # that can resume after a process restart. Never leave a stale row in
        # queued/processing: its idempotency key would otherwise replay a job
        # that no worker owns any more.
        placeholders = ", ".join("?" for _ in SUPPORTED_KINDS)
        interrupted_sql = f"""SELECT id FROM web_image_operations
                WHERE kind IN ({placeholders}) AND state IN ('queued', 'processing')"""
        interrupted_parameters: tuple[str, ...] = tuple(sorted(SUPPORTED_KINDS))
        if interrupted_cutoff:
            interrupted_sql += " AND COALESCE(started_at, queued_at, created_at, updated_at) < ?"
            interrupted_parameters += (interrupted_cutoff,)
        interrupted = conn.execute(interrupted_sql, interrupted_parameters).fetchall()
        for interrupted_row in interrupted:
            operation_id = str(interrupted_row[0])
            conn.execute(
                """UPDATE web_image_operations
                   SET state='failed', failure_code='IMAGE_OPERATION_INTERRUPTED', updated_at=?
                   WHERE id=? AND state IN ('queued', 'processing')""",
                (now, operation_id),
            )
            _record_event(conn, operation_id=operation_id, state="failed", when=now)
        rows = conn.execute(
            f"""SELECT id, account_id, storage_key, byte_size, sha256
                 FROM web_image_operations
                 WHERE kind IN ({placeholders}) AND state='completed'""",
            tuple(sorted(SUPPORTED_KINDS)),
        ).fetchall()
    known_storage: set[str] = set()
    for row in rows:
        operation_id, account_id = str(row[0]), str(row[1])
        private_path: Path | None = None
        try:
            storage_key = str(row[2] or "")
            private_path = _output_path(root, storage_key)
            valid = _verify_file(private_path, expected_bytes=int(row[3] or 0), expected_digest=str(row[4] or ""))
            if valid:
                _verify_output_png(private_path, expected_width=_operation_dimensions(operation_id, account_id)[0], expected_height=_operation_dimensions(operation_id, account_id)[1])
                known_storage.add(storage_key)
        except (ImageOperationError, OSError, RuntimeError):
            valid = False
        if not valid:
            _mark_output_unavailable(operation_id, account_id)
            _safe_unlink(private_path)
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


def _operation_dimensions(operation_id: str, account_id: str) -> tuple[int, int]:
    with transaction() as conn:
        row = conn.execute(
            "SELECT target_width, target_height FROM web_image_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
    if not row:
        raise RuntimeError("Không thể đọc kích thước Image Operation")
    return int(row[0]), int(row[1])


@router.get("")
async def list_image_operations(
    limit: int = 50,
    kind: str | None = None,
    offset: int = Query(0, ge=0, le=10000),
    account: dict = Depends(require_account),
):
    _require_enabled()
    bounded_limit = max(1, min(int(limit), 100))
    normalized_kind = str(kind or "").strip().lower()
    if normalized_kind and normalized_kind not in SUPPORTED_KINDS:
        raise HTTPException(status_code=422, detail="Loại Image Operation không hợp lệ")
    ensure_copyfast_schema()
    with transaction() as conn:
        if normalized_kind:
            rows = conn.execute(
                f"""SELECT {OPERATION_SELECT} FROM web_image_operations
                    WHERE account_id=? AND kind=? ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
                (str(account["id"]), normalized_kind, bounded_limit + 1, int(offset)),
            ).fetchall()
        else:
            history_kinds = tuple(sorted(IMAGE_HISTORY_KINDS))
            placeholders = ", ".join("?" for _ in history_kinds)
            rows = conn.execute(
                f"""SELECT {OPERATION_SELECT} FROM web_image_operations
                    WHERE account_id=? AND kind IN ({placeholders})
                    ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
                (str(account["id"]), *history_kinds, bounded_limit + 1, int(offset)),
            ).fetchall()
    has_more = len(rows) > bounded_limit
    return envelope(
        True,
        "Đã tải các thao tác ảnh riêng tư.",
        data={
            "items": [_operation_public(tuple(row)) for row in rows[:bounded_limit]],
            "has_more": has_more,
            "next_offset": int(offset) + bounded_limit if has_more else None,
        },
        status_name="completed",
    )


@router.post("/resize")
async def resize_image(payload: ImageResizeRequest, request: Request, account: dict = Depends(require_csrf)):
    """Create an owner-scoped verified PNG with crop, pad or blur background."""
    _require_resize_enabled()
    root = image_operations_directory()
    account_id = str(account["id"])
    preset, target_width, target_height, fit_mode = _normalized_spec(payload)
    operation_id = ""
    source_copy: Path | None = None
    final_path: Path | None = None
    capacity_reserved = False
    source_asset_id = payload.source_asset_id
    source_storage_key = ""
    source_extension = ""
    source_bytes = 0
    source_sha256 = ""
    source_width: int | None = None
    source_height: int | None = None

    ensure_copyfast_schema()
    try:
        with transaction() as conn:
            # An idempotency replay is a lookup of the original immutable
            # request, not a new attempt to read the source. It must keep
            # returning the canonical operation even if the owner later
            # archives the source asset or it becomes unavailable.
            existing = conn.execute(
                f"""SELECT {OPERATION_SELECT}, request_fingerprint FROM web_image_operations
                    WHERE account_id=? AND kind=? AND idempotency_key=?""",
                (account_id, IMAGE_RESIZE_KIND, payload.idempotency_key),
            ).fetchone()
            if existing:
                existing_operation = tuple(existing[:-1])
                existing_source_sha256 = str(existing_operation[23] or "")
                existing_source_bytes = int(existing_operation[22] or 0)
                if (
                    re.fullmatch(r"[0-9a-f]{64}", existing_source_sha256)
                    and existing_source_bytes > 0
                    and hmac.compare_digest(
                        str(existing[-1] or ""),
                        _request_fingerprint(
                            source_asset_id=source_asset_id,
                            source_sha256=existing_source_sha256,
                            source_bytes=existing_source_bytes,
                            preset=preset,
                            target_width=target_width,
                            target_height=target_height,
                            fit_mode=fit_mode,
                        ),
                    )
                ):
                    return _operation_response(_operation_public(existing_operation))
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho Resize & Aspect khác")

            source_row = conn.execute(
                """SELECT id, project_id, extension, content_type, byte_size, sha256, storage_key, state
                   FROM web_asset_files WHERE id=? AND account_id=?""",
                (source_asset_id, account_id),
            ).fetchone()
            if not source_row or str(source_row[7]) != "active":
                return _source_not_found()
            source_extension = str(source_row[2] or "").lower()
            expected_mime = IMAGE_INPUT_MIME_BY_EXTENSION.get(source_extension)
            if expected_mime is None or str(source_row[3] or "") != expected_mime:
                raise HTTPException(status_code=422, detail="Resize Studio chỉ nhận JPEG, PNG hoặc WebP private hợp lệ trong Asset Vault")
            source_bytes = int(source_row[4] or 0)
            if source_bytes < 1 or source_bytes > MAX_INPUT_BYTES:
                raise HTTPException(status_code=413, detail="Ảnh nguồn vượt giới hạn 20 MB")
            source_sha256 = str(source_row[5] or "")
            source_storage_key = str(source_row[6] or "")
            if not re.fullmatch(r"[0-9a-f]{64}", source_sha256) or not ASSET_STORAGE_KEY_PATTERN.fullmatch(source_storage_key):
                raise HTTPException(status_code=422, detail="Ảnh nguồn không còn sẵn sàng")
            request_fingerprint = _request_fingerprint(
                source_asset_id=source_asset_id,
                source_sha256=source_sha256,
                source_bytes=source_bytes,
                preset=preset,
                target_width=target_width,
                target_height=target_height,
                fit_mode=fit_mode,
            )
            # Replays are checked before the process-wide decoder gate. A
            # completed operation stays retrievable even while another image
            # feature is actively consuming the single shared Pillow slot.
            capacity = image_decoder_capacity()
            if not capacity.acquire(blocking=False):
                raise HTTPException(status_code=429, detail="Resize Studio đang bận xử lý một ảnh khác; vui lòng thử lại sau ít phút")
            capacity_reserved = True
            operation_id = str(uuid.uuid4())
            now = utc_now()
            conn.execute(
                """INSERT INTO web_image_operations
                   (id, account_id, source_asset_id, project_id, kind, state, idempotency_key,
                    request_fingerprint, source_sha256, source_byte_size, target_width, target_height,
                    preset, fit_mode, created_at, queued_at, started_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    operation_id,
                    account_id,
                    source_asset_id,
                    str(source_row[1]) if source_row[1] else None,
                    IMAGE_RESIZE_KIND,
                    payload.idempotency_key,
                    request_fingerprint,
                    source_sha256,
                    source_bytes,
                    target_width,
                    target_height,
                    preset,
                    fit_mode,
                    now,
                    now,
                    now,
                    now,
                ),
            )
            _record_event(conn, operation_id=operation_id, state="queued", when=now)
            conn.execute(
                "UPDATE web_image_operations SET state='processing', updated_at=? WHERE id=? AND account_id=?",
                (now, operation_id, account_id),
            )
            _record_event(conn, operation_id=operation_id, state="processing", when=now)
    except Exception:
        if capacity_reserved:
            image_decoder_capacity().release()
        raise

    try:
        source_path = _asset_path(asset_vault_directory(), source_storage_key)
        source_copy = _staging_path(root, f".source{source_extension}")
        await run_in_threadpool(
            _copy_verified_image_source,
            source_path,
            source_copy,
            extension=source_extension,
            expected_bytes=source_bytes,
            expected_digest=source_sha256,
        )
        source_width, source_height = await run_in_threadpool(
            _inspect_image_source,
            source_copy,
            extension=source_extension,
        )
        final_path, output_storage_key, output_bytes, output_digest, output_width, output_height = await run_in_threadpool(
            _build_resize_output,
            root,
            source_copy,
            extension=source_extension,
            target_width=target_width,
            target_height=target_height,
            fit_mode=fit_mode,
        )
        now = utc_now()
        with transaction() as conn:
            current = conn.execute(
                "SELECT state FROM web_image_operations WHERE id=? AND account_id=? AND kind=?",
                (operation_id, account_id, IMAGE_RESIZE_KIND),
            ).fetchone()
            if not current or str(current[0]) != "processing":
                raise RuntimeError("Resize Studio không còn ở trạng thái có thể hoàn tất")
            if not _quota_available(conn, account_id=account_id, additional_bytes=output_bytes):
                raise HTTPException(status_code=413, detail="Image Operations đã đạt quota của Web account")
            conn.execute(
                """UPDATE web_image_operations
                   SET state='completed', source_width=?, source_height=?, storage_key=?,
                       original_filename=?, content_type=?, byte_size=?, sha256=?,
                       completed_at=?, updated_at=?, failure_code=NULL
                   WHERE id=? AND account_id=?""",
                (
                    source_width,
                    source_height,
                    output_storage_key,
                    OUTPUT_FILENAME,
                    PNG_MEDIA_TYPE,
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
                action="web.image_operation.image_resize",
                request_id=_request_id(request),
                target=operation_id,
                detail=(
                    f"preset={preset};fit={fit_mode};source={source_width}x{source_height};"
                    f"output={output_width}x{output_height};bytes={output_bytes}"
                ),
            )
            completed = conn.execute(
                f"SELECT {OPERATION_SELECT} FROM web_image_operations WHERE id=? AND account_id=?",
                (operation_id, account_id),
            ).fetchone()
        if not completed:
            raise RuntimeError("Không thể đọc Resize Studio vừa hoàn tất")
        final_path = None
        return _operation_response(_operation_public(tuple(completed)))
    except ImageOperationError as exc:
        _safe_unlink(final_path)
        if exc.code == "IMAGE_SOURCE_UNAVAILABLE":
            _mark_source_unavailable(source_asset_id, account_id)
        _mark_failed(operation_id, account_id, request=request, code=exc.code)
        raise HTTPException(status_code=_image_operation_error_status(exc.code), detail=exc.public_message) from exc
    except HTTPException as exc:
        _safe_unlink(final_path)
        _mark_failed(
            operation_id,
            account_id,
            request=request,
            code="IMAGE_QUOTA" if exc.status_code == 413 else "IMAGE_OPERATION",
        )
        raise
    except Exception as exc:
        _safe_unlink(final_path)
        _mark_failed(operation_id, account_id, request=request, code="IMAGE_OPERATION")
        raise HTTPException(status_code=500, detail="Không thể resize ảnh an toàn") from exc
    finally:
        _safe_unlink(source_copy)
        if capacity_reserved:
            image_decoder_capacity().release()


@router.post("/enhance")
async def enhance_image(payload: ImageEnhanceRequest, request: Request, account: dict = Depends(require_csrf)):
    """Create a verified private PNG with bounded deterministic local enhancement."""
    _require_enhance_enabled()
    root = image_operations_directory()
    account_id = str(account["id"])
    preset, settings = _normalized_enhance_spec(payload)
    settings_json = json.dumps(settings, sort_keys=True, separators=(",", ":"))
    operation_id = ""
    source_copy: Path | None = None
    final_path: Path | None = None
    capacity_reserved = False
    source_asset_id = payload.source_asset_id
    source_storage_key = ""
    source_project_id: str | None = None
    source_extension = ""
    source_bytes = 0
    source_sha256 = ""
    source_width = 0
    source_height = 0
    target_width = 0
    target_height = 0

    ensure_copyfast_schema()
    try:
        with transaction() as conn:
            # Replay is checked before source activity and the shared decoder
            # slot, so an archived source can still return its canonical prior
            # operation without creating a second render or output.
            existing = conn.execute(
                f"""SELECT {OPERATION_SELECT}, request_fingerprint FROM web_image_operations
                    WHERE account_id=? AND kind=? AND idempotency_key=?""",
                (account_id, IMAGE_ENHANCE_KIND, payload.idempotency_key),
            ).fetchone()
            if existing:
                existing_operation = tuple(existing[:-1])
                existing_source_sha256 = str(existing_operation[23] or "")
                existing_source_bytes = int(existing_operation[22] or 0)
                if (
                    re.fullmatch(r"[0-9a-f]{64}", existing_source_sha256)
                    and existing_source_bytes > 0
                    and hmac.compare_digest(
                        str(existing[-1] or ""),
                        _enhance_request_fingerprint(
                            source_asset_id=source_asset_id,
                            source_sha256=existing_source_sha256,
                            source_bytes=existing_source_bytes,
                            preset=preset,
                            settings=settings,
                        ),
                    )
                ):
                    return _operation_response(_operation_public(existing_operation))
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho Image Enhance khác")

            source_row = conn.execute(
                """SELECT id, project_id, extension, content_type, byte_size, sha256, storage_key, state
                   FROM web_asset_files WHERE id=? AND account_id=?""",
                (source_asset_id, account_id),
            ).fetchone()
            if not source_row or str(source_row[7]) != "active":
                return _source_not_found(IMAGE_ENHANCE_KIND)
            source_extension = str(source_row[2] or "").lower()
            source_project_id = str(source_row[1]) if source_row[1] else None
            expected_mime = IMAGE_INPUT_MIME_BY_EXTENSION.get(source_extension)
            if expected_mime is None or str(source_row[3] or "") != expected_mime:
                raise HTTPException(status_code=422, detail="Image Enhance Studio chỉ nhận JPEG, PNG hoặc WebP private hợp lệ trong Asset Vault")
            source_bytes = int(source_row[4] or 0)
            if source_bytes < 1 or source_bytes > MAX_INPUT_BYTES:
                raise HTTPException(status_code=413, detail="Ảnh nguồn vượt giới hạn 20 MB")
            source_sha256 = str(source_row[5] or "")
            source_storage_key = str(source_row[6] or "")
            if not re.fullmatch(r"[0-9a-f]{64}", source_sha256) or not ASSET_STORAGE_KEY_PATTERN.fullmatch(source_storage_key):
                raise HTTPException(status_code=422, detail="Ảnh nguồn không còn sẵn sàng")
            # The one shared Pillow slot is acquired before the isolated copy so
            # a concurrent request cannot race this pre-insert window into a
            # duplicate operation. Replays above never need the slot.
            capacity = image_decoder_capacity()
            if not capacity.acquire(blocking=False):
                raise HTTPException(status_code=429, detail="Image Enhance Studio đang bận xử lý một ảnh khác; vui lòng thử lại sau ít phút")
            capacity_reserved = True
    except Exception:
        if capacity_reserved:
            image_decoder_capacity().release()
        raise

    try:
        source_path = _asset_path(asset_vault_directory(), source_storage_key)
        source_copy = _staging_path(root, f".enhance-source{source_extension}")
        await run_in_threadpool(
            _copy_verified_image_source,
            source_path,
            source_copy,
            extension=source_extension,
            expected_bytes=source_bytes,
            expected_digest=source_sha256,
        )
        # Verify compressed bytes before deriving EXIF-normalized geometry.
        await run_in_threadpool(_inspect_image_source, source_copy, extension=source_extension)
        source_width, source_height, target_width, target_height = await run_in_threadpool(
            _inspect_enhance_geometry,
            source_copy,
            extension=source_extension,
            basic_upscale=bool(settings["basic_upscale"]),
        )

        with transaction() as conn:
            # A second check retains deterministic behaviour if another
            # process inserted the same operation while this request copied the
            # source. It also refuses an archive/tamper transition after copy.
            existing = conn.execute(
                f"""SELECT {OPERATION_SELECT}, request_fingerprint FROM web_image_operations
                    WHERE account_id=? AND kind=? AND idempotency_key=?""",
                (account_id, IMAGE_ENHANCE_KIND, payload.idempotency_key),
            ).fetchone()
            if existing:
                existing_operation = tuple(existing[:-1])
                existing_source_sha256 = str(existing_operation[23] or "")
                existing_source_bytes = int(existing_operation[22] or 0)
                if (
                    re.fullmatch(r"[0-9a-f]{64}", existing_source_sha256)
                    and existing_source_bytes > 0
                    and hmac.compare_digest(
                        str(existing[-1] or ""),
                        _enhance_request_fingerprint(
                            source_asset_id=source_asset_id,
                            source_sha256=existing_source_sha256,
                            source_bytes=existing_source_bytes,
                            preset=preset,
                            settings=settings,
                        ),
                    )
                ):
                    return _operation_response(_operation_public(existing_operation))
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho Image Enhance khác")
            current_source = conn.execute(
                """SELECT byte_size, sha256, storage_key, state FROM web_asset_files
                   WHERE id=? AND account_id=?""",
                (source_asset_id, account_id),
            ).fetchone()
            if (
                not current_source
                or str(current_source[3]) != "active"
                or int(current_source[0] or 0) != source_bytes
                or not hmac.compare_digest(str(current_source[1] or ""), source_sha256)
                or not hmac.compare_digest(str(current_source[2] or ""), source_storage_key)
            ):
                return _source_not_found(IMAGE_ENHANCE_KIND)
            request_fingerprint = _enhance_request_fingerprint(
                source_asset_id=source_asset_id,
                source_sha256=source_sha256,
                source_bytes=source_bytes,
                preset=preset,
                settings=settings,
            )
            operation_id = str(uuid.uuid4())
            now = utc_now()
            conn.execute(
                """INSERT INTO web_image_operations
                   (id, account_id, source_asset_id, project_id, kind, state, idempotency_key,
                    request_fingerprint, source_sha256, source_byte_size, target_width, target_height,
                    preset, fit_mode, settings_json, created_at, queued_at, started_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    operation_id,
                    account_id,
                    source_asset_id,
                    source_project_id,
                    IMAGE_ENHANCE_KIND,
                    payload.idempotency_key,
                    request_fingerprint,
                    source_sha256,
                    source_bytes,
                    target_width,
                    target_height,
                    preset,
                    ENHANCE_FIT_MODE,
                    settings_json,
                    now,
                    now,
                    now,
                    now,
                ),
            )
            _record_event(conn, operation_id=operation_id, state="queued", when=now)
            conn.execute(
                "UPDATE web_image_operations SET state='processing', updated_at=? WHERE id=? AND account_id=?",
                (now, operation_id, account_id),
            )
            _record_event(conn, operation_id=operation_id, state="processing", when=now)

        final_path, output_storage_key, output_bytes, output_digest, output_width, output_height = await run_in_threadpool(
            _build_enhance_output,
            root,
            source_copy,
            extension=source_extension,
            settings=settings,
            target_width=target_width,
            target_height=target_height,
        )
        now = utc_now()
        with transaction() as conn:
            current = conn.execute(
                "SELECT state FROM web_image_operations WHERE id=? AND account_id=? AND kind=?",
                (operation_id, account_id, IMAGE_ENHANCE_KIND),
            ).fetchone()
            if not current or str(current[0]) != "processing":
                raise RuntimeError("Image Enhance Studio không còn ở trạng thái có thể hoàn tất")
            if not _quota_available(conn, account_id=account_id, additional_bytes=output_bytes):
                raise HTTPException(status_code=413, detail="Image Operations đã đạt quota của Web account")
            conn.execute(
                """UPDATE web_image_operations
                   SET state='completed', source_width=?, source_height=?, target_width=?, target_height=?, storage_key=?,
                       original_filename=?, content_type=?, byte_size=?, sha256=?,
                       completed_at=?, updated_at=?, failure_code=NULL
                   WHERE id=? AND account_id=?""",
                (
                    source_width,
                    source_height,
                    output_width,
                    output_height,
                    output_storage_key,
                    ENHANCE_OUTPUT_FILENAME,
                    PNG_MEDIA_TYPE,
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
                action="web.image_operation.image_enhance",
                request_id=_request_id(request),
                target=operation_id,
                detail=(
                    f"preset={preset};upscale={int(bool(settings['basic_upscale']))};"
                    f"source={source_width}x{source_height};output={output_width}x{output_height};bytes={output_bytes}"
                ),
            )
            completed = conn.execute(
                f"SELECT {OPERATION_SELECT} FROM web_image_operations WHERE id=? AND account_id=?",
                (operation_id, account_id),
            ).fetchone()
        if not completed:
            raise RuntimeError("Không thể đọc Image Enhance Studio vừa hoàn tất")
        final_path = None
        return _operation_response(_operation_public(tuple(completed)))
    except ImageOperationError as exc:
        _safe_unlink(final_path)
        if exc.code == "IMAGE_SOURCE_UNAVAILABLE":
            _mark_source_unavailable(source_asset_id, account_id)
        _mark_failed(operation_id, account_id, request=request, code=exc.code, kind=IMAGE_ENHANCE_KIND)
        raise HTTPException(status_code=_image_operation_error_status(exc.code), detail=exc.public_message) from exc
    except HTTPException as exc:
        _safe_unlink(final_path)
        _mark_failed(
            operation_id,
            account_id,
            request=request,
            code="IMAGE_QUOTA" if exc.status_code == 413 else "IMAGE_OPERATION",
            kind=IMAGE_ENHANCE_KIND,
        )
        raise
    except Exception as exc:
        _safe_unlink(final_path)
        _mark_failed(operation_id, account_id, request=request, code="IMAGE_OPERATION", kind=IMAGE_ENHANCE_KIND)
        raise HTTPException(status_code=500, detail="Không thể chỉnh ảnh an toàn") from exc
    finally:
        _safe_unlink(source_copy)
        if capacity_reserved:
            image_decoder_capacity().release()


@router.post("/brand-overlay")
async def create_brand_overlay(
    payload: ImageBrandOverlayRequest,
    request: Request,
    account: dict = Depends(require_csrf),
):
    """Create a verified private PNG with local text and/or logo composition.

    The operation deliberately accepts only Asset Vault IDs.  It never accepts
    browser image bytes, URLs, paths or fonts, never alters the source asset,
    and does not call the Bot, a provider, PayOS, wallet or job system.
    """
    _require_brand_overlay_enabled()
    root = image_operations_directory()
    account_id = str(account["id"])
    spec = _normalized_brand_overlay_spec(payload)
    overlay_text = str(spec["overlay_text"]) if spec["overlay_text"] else None
    text_position = str(spec["text_position"])
    logo_asset_id = str(spec["logo_asset_id"]) if spec["logo_asset_id"] else None
    logo_position = str(spec["logo_position"])
    logo_scale_percent = int(spec["logo_scale_percent"])
    logo_opacity_percent = int(spec["logo_opacity_percent"])
    source_asset_id = payload.source_asset_id
    operation_id = ""
    source_copy: Path | None = None
    logo_copy: Path | None = None
    final_path: Path | None = None
    capacity_reserved = False
    source_storage_key = ""
    source_project_id: str | None = None
    source_extension = ""
    source_bytes = 0
    source_sha256 = ""
    logo_storage_key = ""
    logo_extension = ""
    logo_bytes = 0
    logo_sha256 = ""
    source_width = 0
    source_height = 0
    target_width = 0
    target_height = 0

    ensure_copyfast_schema()
    try:
        with transaction() as conn:
            # A prior immutable request must replay before any live asset
            # lookup.  This lets an owner retrieve the original verified PNG
            # even after the original source/logo was archived.
            existing = conn.execute(
                f"""SELECT {OPERATION_SELECT}, request_fingerprint FROM web_image_operations
                    WHERE account_id=? AND kind=? AND idempotency_key=?""",
                (account_id, IMAGE_BRAND_OVERLAY_KIND, payload.idempotency_key),
            ).fetchone()
            if existing:
                existing_operation = tuple(existing[:-1])
                if _brand_overlay_replay_matches(
                    existing_operation,
                    existing[-1],
                    source_asset_id=source_asset_id,
                    overlay_text=overlay_text,
                    text_position=text_position,
                    logo_asset_id=logo_asset_id,
                    logo_position=logo_position,
                    logo_scale_percent=logo_scale_percent,
                    logo_opacity_percent=logo_opacity_percent,
                ):
                    return _operation_response(_operation_public(existing_operation))
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho Brand Overlay khác")

            source_row = conn.execute(
                """SELECT id, project_id, extension, content_type, byte_size, sha256, storage_key, state
                   FROM web_asset_files WHERE id=? AND account_id=?""",
                (source_asset_id, account_id),
            ).fetchone()
            if not source_row or str(source_row[7]) != "active":
                return _source_not_found(IMAGE_BRAND_OVERLAY_KIND)
            source_extension = str(source_row[2] or "").lower()
            expected_source_mime = IMAGE_INPUT_MIME_BY_EXTENSION.get(source_extension)
            if expected_source_mime is None or str(source_row[3] or "") != expected_source_mime:
                raise HTTPException(status_code=422, detail="Brand Overlay Studio chỉ nhận JPEG, PNG hoặc WebP private hợp lệ trong Asset Vault")
            source_bytes = int(source_row[4] or 0)
            source_sha256 = str(source_row[5] or "")
            source_storage_key = str(source_row[6] or "")
            source_project_id = str(source_row[1]) if source_row[1] else None
            if source_bytes < 1 or source_bytes > MAX_INPUT_BYTES:
                raise HTTPException(status_code=413, detail="Ảnh nguồn vượt giới hạn 20 MB")
            if re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None or not ASSET_STORAGE_KEY_PATTERN.fullmatch(source_storage_key):
                raise HTTPException(status_code=422, detail="Ảnh nguồn không còn sẵn sàng")

            if logo_asset_id:
                logo_row = conn.execute(
                    """SELECT id, extension, content_type, byte_size, sha256, storage_key, state
                       FROM web_asset_files WHERE id=? AND account_id=?""",
                    (logo_asset_id, account_id),
                ).fetchone()
                if not logo_row or str(logo_row[6]) != "active":
                    return _logo_not_found()
                logo_extension = str(logo_row[1] or "").lower()
                expected_logo_mime = IMAGE_INPUT_MIME_BY_EXTENSION.get(logo_extension)
                if expected_logo_mime is None or str(logo_row[2] or "") != expected_logo_mime:
                    raise HTTPException(status_code=422, detail="Logo chỉ nhận JPEG, PNG hoặc WebP private hợp lệ trong Asset Vault")
                logo_bytes = int(logo_row[3] or 0)
                logo_sha256 = str(logo_row[4] or "")
                logo_storage_key = str(logo_row[5] or "")
                if logo_bytes < 1 or logo_bytes > MAX_INPUT_BYTES:
                    raise HTTPException(status_code=413, detail="Logo vượt giới hạn 20 MB")
                if re.fullmatch(r"[0-9a-f]{64}", logo_sha256) is None or not ASSET_STORAGE_KEY_PATTERN.fullmatch(logo_storage_key):
                    raise HTTPException(status_code=422, detail="Logo không còn sẵn sàng")

            # One shared decoder slot covers both source and logo decoding.
            # This serializes the decoder-heavy path while allowing prior
            # idempotent requests to return instantly above.
            capacity = image_decoder_capacity()
            if not capacity.acquire(blocking=False):
                raise HTTPException(status_code=429, detail="Brand Overlay Studio đang bận xử lý một ảnh khác; vui lòng thử lại sau ít phút")
            capacity_reserved = True
    except Exception:
        if capacity_reserved:
            image_decoder_capacity().release()
        raise

    try:
        source_path = _asset_path(asset_vault_directory(), source_storage_key)
        source_copy = _staging_path(root, f".brand-source{source_extension}")
        await run_in_threadpool(
            _copy_verified_image_source,
            source_path,
            source_copy,
            extension=source_extension,
            expected_bytes=source_bytes,
            expected_digest=source_sha256,
        )
        await run_in_threadpool(_inspect_image_source, source_copy, extension=source_extension)
        source_width, source_height, target_width, target_height = await run_in_threadpool(
            _inspect_brand_overlay_geometry,
            source_copy,
            extension=source_extension,
        )
        if logo_asset_id:
            logo_path = _asset_path(asset_vault_directory(), logo_storage_key)
            logo_copy = _staging_path(root, f".brand-logo{logo_extension}")
            try:
                await run_in_threadpool(
                    _copy_verified_image_source,
                    logo_path,
                    logo_copy,
                    extension=logo_extension,
                    expected_bytes=logo_bytes,
                    expected_digest=logo_sha256,
                )
            except ImageOperationError as exc:
                if exc.code == "IMAGE_SOURCE_UNAVAILABLE":
                    raise ImageOperationError("Logo private không còn sẵn sàng", code="IMAGE_LOGO_UNAVAILABLE") from exc
                raise
            await run_in_threadpool(_inspect_image_source, logo_copy, extension=logo_extension)

        with transaction() as conn:
            # Recheck after isolated copies: the source and optional logo must
            # still be the same active immutable blobs before an operation row
            # can be accepted.
            existing = conn.execute(
                f"""SELECT {OPERATION_SELECT}, request_fingerprint FROM web_image_operations
                    WHERE account_id=? AND kind=? AND idempotency_key=?""",
                (account_id, IMAGE_BRAND_OVERLAY_KIND, payload.idempotency_key),
            ).fetchone()
            if existing:
                existing_operation = tuple(existing[:-1])
                if _brand_overlay_replay_matches(
                    existing_operation,
                    existing[-1],
                    source_asset_id=source_asset_id,
                    overlay_text=overlay_text,
                    text_position=text_position,
                    logo_asset_id=logo_asset_id,
                    logo_position=logo_position,
                    logo_scale_percent=logo_scale_percent,
                    logo_opacity_percent=logo_opacity_percent,
                ):
                    return _operation_response(_operation_public(existing_operation))
                raise HTTPException(status_code=409, detail="Idempotency key đã được dùng cho Brand Overlay khác")
            current_source = conn.execute(
                """SELECT byte_size, sha256, storage_key, state FROM web_asset_files
                   WHERE id=? AND account_id=?""",
                (source_asset_id, account_id),
            ).fetchone()
            if (
                not current_source
                or str(current_source[3]) != "active"
                or int(current_source[0] or 0) != source_bytes
                or not hmac.compare_digest(str(current_source[1] or ""), source_sha256)
                or not hmac.compare_digest(str(current_source[2] or ""), source_storage_key)
            ):
                return _source_not_found(IMAGE_BRAND_OVERLAY_KIND)
            if logo_asset_id:
                current_logo = conn.execute(
                    """SELECT byte_size, sha256, storage_key, state FROM web_asset_files
                       WHERE id=? AND account_id=?""",
                    (logo_asset_id, account_id),
                ).fetchone()
                if (
                    not current_logo
                    or str(current_logo[3]) != "active"
                    or int(current_logo[0] or 0) != logo_bytes
                    or not hmac.compare_digest(str(current_logo[1] or ""), logo_sha256)
                    or not hmac.compare_digest(str(current_logo[2] or ""), logo_storage_key)
                ):
                    return _logo_not_found()
            storage_settings = _brand_overlay_storage_settings(
                overlay_text=overlay_text,
                text_position=text_position,
                logo_asset_id=logo_asset_id,
                logo_sha256=logo_sha256 if logo_asset_id else None,
                logo_bytes=logo_bytes if logo_asset_id else 0,
                logo_position=logo_position,
                logo_scale_percent=logo_scale_percent,
                logo_opacity_percent=logo_opacity_percent,
            )
            request_fingerprint = _brand_overlay_request_fingerprint(
                source_asset_id=source_asset_id,
                source_sha256=source_sha256,
                source_bytes=source_bytes,
                logo_asset_id=logo_asset_id,
                logo_sha256=logo_sha256 if logo_asset_id else None,
                logo_bytes=logo_bytes if logo_asset_id else 0,
                overlay_text=overlay_text,
                text_position=text_position,
                logo_position=logo_position,
                logo_scale_percent=logo_scale_percent,
                logo_opacity_percent=logo_opacity_percent,
            )
            operation_id = str(uuid.uuid4())
            now = utc_now()
            conn.execute(
                """INSERT INTO web_image_operations
                   (id, account_id, source_asset_id, project_id, kind, state, idempotency_key,
                    request_fingerprint, source_sha256, source_byte_size, target_width, target_height,
                    preset, fit_mode, settings_json, created_at, queued_at, started_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    operation_id,
                    account_id,
                    source_asset_id,
                    source_project_id,
                    IMAGE_BRAND_OVERLAY_KIND,
                    payload.idempotency_key,
                    request_fingerprint,
                    source_sha256,
                    source_bytes,
                    target_width,
                    target_height,
                    BRAND_OVERLAY_PRESET,
                    BRAND_OVERLAY_FIT_MODE,
                    json.dumps(storage_settings, sort_keys=True, separators=(",", ":")),
                    now,
                    now,
                    now,
                    now,
                ),
            )
            _record_event(conn, operation_id=operation_id, state="queued", when=now)
            conn.execute(
                "UPDATE web_image_operations SET state='processing', updated_at=? WHERE id=? AND account_id=?",
                (now, operation_id, account_id),
            )
            _record_event(conn, operation_id=operation_id, state="processing", when=now)

        final_path, output_storage_key, output_bytes, output_digest, output_width, output_height = await run_in_threadpool(
            _build_brand_overlay_output,
            root,
            source_copy,
            source_extension=source_extension,
            target_width=target_width,
            target_height=target_height,
            overlay_text=overlay_text,
            text_position=text_position,
            logo_copy=logo_copy,
            logo_extension=logo_extension if logo_asset_id else None,
            logo_position=logo_position,
            logo_scale_percent=logo_scale_percent,
            logo_opacity_percent=logo_opacity_percent,
        )
        now = utc_now()
        with transaction() as conn:
            current = conn.execute(
                "SELECT state FROM web_image_operations WHERE id=? AND account_id=? AND kind=?",
                (operation_id, account_id, IMAGE_BRAND_OVERLAY_KIND),
            ).fetchone()
            if not current or str(current[0]) != "processing":
                raise RuntimeError("Brand Overlay Studio không còn ở trạng thái có thể hoàn tất")
            if not _quota_available(conn, account_id=account_id, additional_bytes=output_bytes):
                raise HTTPException(status_code=413, detail="Image Operations đã đạt quota của Web account")
            conn.execute(
                """UPDATE web_image_operations
                   SET state='completed', source_width=?, source_height=?, target_width=?, target_height=?, storage_key=?,
                       original_filename=?, content_type=?, byte_size=?, sha256=?,
                       completed_at=?, updated_at=?, failure_code=NULL
                   WHERE id=? AND account_id=?""",
                (
                    source_width,
                    source_height,
                    output_width,
                    output_height,
                    output_storage_key,
                    BRAND_OVERLAY_OUTPUT_FILENAME,
                    PNG_MEDIA_TYPE,
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
                action="web.image_operation.image_brand_overlay",
                request_id=_request_id(request),
                target=operation_id,
                detail=(
                    f"text={int(bool(overlay_text))};logo={int(bool(logo_asset_id))};"
                    f"text_position={text_position};logo_position={logo_position};"
                    f"logo_scale={logo_scale_percent};logo_opacity={logo_opacity_percent};"
                    f"source={source_width}x{source_height};output={output_width}x{output_height};bytes={output_bytes}"
                ),
            )
            completed = conn.execute(
                f"SELECT {OPERATION_SELECT} FROM web_image_operations WHERE id=? AND account_id=?",
                (operation_id, account_id),
            ).fetchone()
        if not completed:
            raise RuntimeError("Không thể đọc Brand Overlay Studio vừa hoàn tất")
        final_path = None
        return _operation_response(_operation_public(tuple(completed)))
    except ImageOperationError as exc:
        _safe_unlink(final_path)
        if exc.code == "IMAGE_SOURCE_UNAVAILABLE":
            _mark_source_unavailable(source_asset_id, account_id)
        elif exc.code == "IMAGE_LOGO_UNAVAILABLE" and logo_asset_id:
            _mark_source_unavailable(logo_asset_id, account_id)
        _mark_failed(operation_id, account_id, request=request, code=exc.code, kind=IMAGE_BRAND_OVERLAY_KIND)
        raise HTTPException(status_code=_image_operation_error_status(exc.code), detail=exc.public_message) from exc
    except HTTPException as exc:
        _safe_unlink(final_path)
        _mark_failed(
            operation_id,
            account_id,
            request=request,
            code="IMAGE_QUOTA" if exc.status_code == 413 else "IMAGE_OPERATION",
            kind=IMAGE_BRAND_OVERLAY_KIND,
        )
        raise
    except Exception as exc:
        _safe_unlink(final_path)
        _mark_failed(operation_id, account_id, request=request, code="IMAGE_OPERATION", kind=IMAGE_BRAND_OVERLAY_KIND)
        raise HTTPException(status_code=500, detail="Không thể tạo Brand Overlay an toàn") from exc
    finally:
        _safe_unlink(source_copy)
        _safe_unlink(logo_copy)
        if capacity_reserved:
            image_decoder_capacity().release()


@router.get("/{operation_id}/download")
async def download_image_operation(operation_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã thao tác ảnh")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            f"SELECT {OPERATION_SELECT} FROM web_image_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
    if not row or str(row[4]) != "completed":
        return _operation_not_found()
    private_path: Path | None = None
    try:
        operation_kind = str(row[3] or "")
        if operation_kind not in SUPPORTED_KINDS or str(row[12] or "") != PNG_MEDIA_TYPE:
            raise RuntimeError("Artifact Image Operation có MIME không hợp lệ")
        private_path = _output_path(image_operations_directory(), str(row[20] or ""))
        verified_stream = _open_verified_output_stream(
            private_path,
            expected_bytes=int(row[13] or 0),
            expected_digest=str(row[21] or ""),
            expected_width=int(row[5]),
            expected_height=int(row[6]),
        )
    except (ImageOperationError, OSError, RuntimeError):
        _mark_output_unavailable(operation_id, account_id)
        _safe_unlink(private_path)
        return _operation_unavailable()
    return StreamingResponse(
        _stream_open_file(verified_stream),
        media_type=PNG_MEDIA_TYPE,
        # The response owns this descriptor even if a disconnect happens
        # before Starlette advances the synchronous generator for the first
        # time. close() is idempotent with the generator's own finally block.
        background=BackgroundTask(verified_stream.close),
        headers={
            "Content-Length": str(int(row[13] or 0)),
            "Content-Disposition": f'attachment; filename="{_operation_output_filename(operation_kind)}"',
            "Cache-Control": "no-store, private",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.get("/{operation_id}")
async def get_image_operation(operation_id: str, account: dict = Depends(require_account)):
    _require_enabled()
    operation_id = _uuid(operation_id, label="Mã thao tác ảnh")
    account_id = str(account["id"])
    ensure_copyfast_schema()
    with transaction() as conn:
        row = conn.execute(
            f"SELECT {OPERATION_SELECT} FROM web_image_operations WHERE id=? AND account_id=?",
            (operation_id, account_id),
        ).fetchone()
        events = conn.execute(
            """SELECT state, created_at FROM web_image_operation_events
               WHERE operation_id=? ORDER BY sequence ASC, id ASC LIMIT 20""",
            (operation_id,),
        ).fetchall()
    if not row:
        return _operation_not_found()
    return envelope(
        True,
        "Đã tải trạng thái thao tác ảnh.",
        data={
            "operation": _operation_public(tuple(row)),
            "events": [{"state": str(event[0]), "created_at": str(event[1])} for event in events],
        },
        status_name=str(row[4]) if str(row[4]) in OPERATION_STATES else "guarded",
    )
