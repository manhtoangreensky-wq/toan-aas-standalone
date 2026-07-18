"""Read-only projections for private Web-native jobs and Asset Vault files.

This module is deliberately a small boundary for a future generic Jobs / Assets
read API.  It reads only existing Web-owned tables and never creates schema,
touches private blobs, imports a Bot/bridge/provider module, or executes an
operation.  Callers must already have authenticated the Web account and must
not turn the metadata-only ``output`` projection into an unverified download.
"""

from __future__ import annotations

import base64
import binascii
import re
from typing import Any

from copyfast_db import (
    frame_video_operations_enabled,
    read_transaction,
    subtitle_asset_operations_enabled,
    video_transform_operations_enabled,
)
from copyfast_subtitle_asset_operations import verified_subtitle_asset_output_available


MAX_LIST_LIMIT = 100
MAX_PUBLIC_ID_LENGTH = 160

_JOB_PREFIX = "wnj:v1"
_ASSET_PREFIX = "wna:v1"
_JOB_SOURCES = frozenset(
    {
        "project-package",
        "document-operation",
        "image-operation",
        "subtitle-asset-operation",
        "video-operation",
        "frame-video-operation",
        "video-transform-operation",
    }
)
_PUBLIC_ROUTE_ID_PATTERN = re.compile(rf"^[A-Za-z0-9._:-]{{1,{MAX_PUBLIC_ID_LENGTH}}}$")
# The longest public job prefix is ``wnj:v1:document-operation:`` (26
# characters).  One hundred ASCII identifier bytes encode to 134 unpadded
# base64url characters, producing an exactly 160-character route ID.
_INTERNAL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_MEDIA_TYPE_PATTERN = re.compile(r"^[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+$")
_PACKAGE_STORAGE_KEY_PATTERN = re.compile(r"^packages/[0-9a-f]{32}\.zip$")
_DOCUMENT_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.(?:pdf|docx|png|txt|zip)$")
_IMAGE_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.png$")
_SUBTITLE_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.(?:srt|vtt)$")
_VIDEO_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.jpg$")
_FRAME_VIDEO_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.mp4$")
_VIDEO_TRANSFORM_STORAGE_KEY_PATTERN = re.compile(r"^outputs/[0-9a-f]{32}\.mp4$")

# These are exact copies of the direct document-handler output contracts.  Do
# not normalize a MIME parameter here: ``text/plain`` is *not* the same sealed
# output as the direct handler's ``text/plain; charset=utf-8`` OCR contract.
_DOCUMENT_OUTPUT_SPECS: dict[str, tuple[str, str, str]] = {
    "pdf_split": (".pdf", "application/pdf", "toan-aas-pdf-split.pdf"),
    "pdf_merge": (".pdf", "application/pdf", "toan-aas-pdf-merged.pdf"),
    "pdf_optimize": (".pdf", "application/pdf", "toan-aas-pdf-optimized.pdf"),
    "image_to_pdf": (".pdf", "application/pdf", "toan-aas-images.pdf"),
    "pdf_to_images": (".zip", "application/zip", "toan-aas-pdf-pages.zip"),
    "pdf_to_word_text": (
        ".docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "toan-aas-pdf-text.docx",
    ),
    "image_ocr": (".txt", "text/plain; charset=utf-8", "toan-aas-image-ocr.txt"),
    "pdf_ocr": (".txt", "text/plain; charset=utf-8", "toan-aas-pdf-ocr.txt"),
}
_PDF_TO_IMAGES_SINGLE_PAGE_SPEC = (".png", "image/png", "toan-aas-pdf-page-001.png")
_PACKAGE_OUTPUT_SPEC = (".zip", "application/zip", "project-package.zip")
_IMAGE_OUTPUT_SPECS: dict[str, tuple[str, str, str]] = {
    "image_resize": (".png", "image/png", "toan-aas-image-resized.png"),
    "image_enhance": (".png", "image/png", "toan-aas-image-enhanced.png"),
}
_SUBTITLE_OUTPUT_SPECS: dict[str, tuple[str, str, str]] = {
    "srt": (".srt", "application/x-subrip", "toan-aas-subtitle.srt"),
    "vtt": (".vtt", "text/vtt", "toan-aas-subtitle.vtt"),
}
_VIDEO_POSTER_OUTPUT_SPEC = (".jpg", "image/jpeg", "toan-aas-video-poster.jpg")
_FRAME_VIDEO_OUTPUT_SPEC = (".mp4", "video/mp4", "toan-aas-frame-video.mp4")
_VIDEO_TRANSFORM_OUTPUT_SPEC = (".mp4", "video/mp4", "toan-aas-video-finished.mp4")


def _account_id(value: Any) -> str:
    """Return a non-empty account identifier without exposing it downstream."""

    candidate = str(value or "").strip()
    return candidate if candidate else ""


def _bounded_limit(value: Any) -> int:
    """Keep all aggregate reads bounded even when called outside a router."""

    try:
        requested = int(value)
    except (TypeError, ValueError):
        requested = MAX_LIST_LIMIT
    return max(1, min(requested, MAX_LIST_LIMIT))


def _text(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _timestamp(value: Any) -> str | None:
    value = _text(value)
    return value if value else None


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _positive_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 and parsed == parsed and parsed not in {float("inf"), float("-inf")} else None


def _safe_filename(value: Any) -> str | None:
    """Return only a basename, never a stored local/private path."""

    raw = _text(value)
    if not raw:
        return None
    basename = raw.replace("\\", "/").rsplit("/", 1)[-1]
    basename = "".join(character for character in basename if ord(character) >= 32 and ord(character) != 127).strip()
    return basename[:255] or None


def _safe_media_type(value: Any) -> str | None:
    """Keep only a conventional MIME type, dropping parameters and junk."""

    raw = _text(value)
    if not raw:
        return None
    media_type = raw.split(";", 1)[0].strip().lower()
    return media_type if _MEDIA_TYPE_PATTERN.fullmatch(media_type) else None


def _encode_identifier(value: Any) -> str:
    """Encode a database identifier without placing it directly in a route."""

    internal_id = str(value or "")
    if not _INTERNAL_IDENTIFIER_PATTERN.fullmatch(internal_id):
        raise ValueError("Web-native record identifier is not eligible for a public projection")
    # URL-safe base64 normally uses ``_``, while this app's route grammar does
    # not.  ``.`` is outside that alphabet, so the substitution is reversible
    # and remains within the existing [A-Za-z0-9._:-] route contract.
    return base64.urlsafe_b64encode(internal_id.encode("utf-8")).decode("ascii").rstrip("=").replace("_", ".")


def _decode_identifier(value: str) -> str | None:
    if not value or not re.fullmatch(r"[A-Za-z0-9.-]+", value):
        return None
    padded = value.replace(".", "_") + ("=" * (-len(value) % 4))
    try:
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True).decode("utf-8")
    except (UnicodeDecodeError, binascii.Error, ValueError):
        return None
    return decoded if _INTERNAL_IDENTIFIER_PATTERN.fullmatch(decoded) else None


def encode_native_job_id(source: str, internal_id: Any) -> str:
    """Create the stable opaque route identifier for one supported job source."""

    if source not in _JOB_SOURCES:
        raise ValueError("Unknown Web-native job source")
    public_id = f"{_JOB_PREFIX}:{source}:{_encode_identifier(internal_id)}"
    if len(public_id) > MAX_PUBLIC_ID_LENGTH:
        raise ValueError("Web-native public job identifier exceeds the route limit")
    return public_id


def parse_native_job_id(public_id: Any) -> tuple[str, str] | None:
    """Parse a supported public job ID, returning ``None`` for every unknown ID."""

    if not isinstance(public_id, str) or not _PUBLIC_ROUTE_ID_PATTERN.fullmatch(public_id):
        return None
    parts = public_id.split(":")
    if len(parts) != 4 or parts[0] != "wnj" or parts[1] != "v1" or parts[2] not in _JOB_SOURCES:
        return None
    internal_id = _decode_identifier(parts[3])
    return (parts[2], internal_id) if internal_id else None


# A clearer alias for router code and contract readers.  Keep both names so a
# future adapter need not know this module's internal naming convention.
parse_public_job_id = parse_native_job_id


def encode_native_asset_id(internal_id: Any) -> str:
    """Create the stable opaque public identifier for an Asset Vault row."""

    public_id = f"{_ASSET_PREFIX}:{_encode_identifier(internal_id)}"
    if len(public_id) > MAX_PUBLIC_ID_LENGTH:
        raise ValueError("Web-native public asset identifier exceeds the route limit")
    return public_id


def parse_native_asset_id(public_id: Any) -> str | None:
    if not isinstance(public_id, str) or not _PUBLIC_ROUTE_ID_PATTERN.fullmatch(public_id):
        return None
    parts = public_id.split(":")
    if len(parts) != 3 or parts[0] != "wna" or parts[1] != "v1":
        return None
    return _decode_identifier(parts[2])


def _document_output_spec(kind: str, output_page_count: Any) -> tuple[str, str, str] | None:
    """Mirror the direct handler's exact PDF-to-images page-count branch."""

    if kind == "pdf_to_images" and _integer(output_page_count) == 1:
        return _PDF_TO_IMAGES_SINGLE_PAGE_SPEC
    return _DOCUMENT_OUTPUT_SPECS.get(kind)


def _sealed_output(
    *,
    state: Any,
    storage_key: Any,
    storage_pattern: re.Pattern[str],
    content_type: Any,
    byte_size: Any,
    sha256: Any,
    expected_suffix: str,
    expected_content_type: str,
    filename: str,
    require_stored_content_type: bool = True,
    required_positive_values: tuple[Any, ...] = (),
) -> dict[str, Any] | None:
    """Project a metadata-complete private output without exposing its locator.

    This intentionally does *not* check the filesystem or create a download
    URL.  Existing download handlers keep the final storage integrity check.
    """

    if str(state or "") != "completed" or not storage_pattern.fullmatch(str(storage_key or "")):
        return None
    safe_byte_size = _positive_int(byte_size)
    if (
        safe_byte_size is None
        or not _SHA256_PATTERN.fullmatch(str(sha256 or "").lower())
        or not str(storage_key).lower().endswith(expected_suffix)
        or (require_stored_content_type and str(content_type or "") != expected_content_type)
        or any(_positive_int(value) is None for value in required_positive_values)
    ):
        return None
    return {
        "filename": filename,
        "content_type": expected_content_type,
        "byte_size": safe_byte_size,
    }


def _project_package(row: tuple[Any, ...]) -> dict[str, Any]:
    (
        record_id,
        state,
        document_count,
        asset_reference_count,
        storage_key,
        filename,
        content_type,
        byte_size,
        sha256,
        created_at,
        queued_at,
        started_at,
        completed_at,
        updated_at,
    ) = row
    exact_state = str(state or "")
    return {
        "id": encode_native_job_id("project-package", record_id),
        "kind": "project-package",
        "state": exact_state,
        "status": exact_state,
        "created_at": _timestamp(created_at),
        "queued_at": _timestamp(queued_at),
        "started_at": _timestamp(started_at),
        "completed_at": _timestamp(completed_at),
        "updated_at": _timestamp(updated_at),
        "summary": {
            "document_count": _non_negative_int(document_count),
            "asset_reference_count": _non_negative_int(asset_reference_count),
        },
        "output": _sealed_output(
            state=state,
            storage_key=storage_key,
            storage_pattern=_PACKAGE_STORAGE_KEY_PATTERN,
            content_type=content_type,
            byte_size=byte_size,
            sha256=sha256,
            expected_suffix=_PACKAGE_OUTPUT_SPEC[0],
            expected_content_type=_PACKAGE_OUTPUT_SPEC[1],
            filename=_safe_filename(filename) or _PACKAGE_OUTPUT_SPEC[2],
            # The direct package downloader always serves a ZIP and does not
            # treat its descriptive table MIME as delivery authority.
            require_stored_content_type=False,
        ),
    }


def _project_document_operation(row: tuple[Any, ...]) -> dict[str, Any]:
    (
        record_id,
        operation_kind,
        state,
        source_count,
        selected_start_page,
        selected_end_page,
        source_page_count,
        output_page_count,
        storage_key,
        filename,
        content_type,
        byte_size,
        sha256,
        created_at,
        queued_at,
        started_at,
        completed_at,
        updated_at,
    ) = row
    exact_state = str(state or "")
    kind = str(operation_kind or "")
    output_spec = _document_output_spec(kind, output_page_count)
    return {
        "id": encode_native_job_id("document-operation", record_id),
        "kind": "document-operation",
        "operation_kind": kind,
        "state": exact_state,
        "status": exact_state,
        "created_at": _timestamp(created_at),
        "queued_at": _timestamp(queued_at),
        "started_at": _timestamp(started_at),
        "completed_at": _timestamp(completed_at),
        "updated_at": _timestamp(updated_at),
        "summary": {
            "source_count": _positive_int(source_count),
            "selected_start_page": _positive_int(selected_start_page),
            "selected_end_page": _positive_int(selected_end_page),
            "source_page_count": _positive_int(source_page_count),
            "output_page_count": _positive_int(output_page_count),
        },
        "output": (
            _sealed_output(
                state=state,
                storage_key=storage_key,
                storage_pattern=_DOCUMENT_STORAGE_KEY_PATTERN,
                content_type=content_type,
                byte_size=byte_size,
                sha256=sha256,
                expected_suffix=output_spec[0],
                expected_content_type=output_spec[1],
                filename=output_spec[2],
            )
            if output_spec is not None
            else None
        ),
    }


def _project_image_operation(row: tuple[Any, ...]) -> dict[str, Any]:
    (
        record_id,
        operation_kind,
        state,
        target_width,
        target_height,
        preset,
        fit_mode,
        source_width,
        source_height,
        storage_key,
        filename,
        content_type,
        byte_size,
        sha256,
        created_at,
        queued_at,
        started_at,
        completed_at,
        updated_at,
    ) = row
    exact_state = str(state or "")
    kind = str(operation_kind or "")
    output_spec = _IMAGE_OUTPUT_SPECS.get(kind)
    return {
        "id": encode_native_job_id("image-operation", record_id),
        "kind": "image-operation",
        "operation_kind": kind,
        "state": exact_state,
        "status": exact_state,
        "created_at": _timestamp(created_at),
        "queued_at": _timestamp(queued_at),
        "started_at": _timestamp(started_at),
        "completed_at": _timestamp(completed_at),
        "updated_at": _timestamp(updated_at),
        "summary": {
            "target_width": _positive_int(target_width),
            "target_height": _positive_int(target_height),
            "preset": _safe_filename(preset),
            "fit_mode": _safe_filename(fit_mode),
            "source_width": _positive_int(source_width),
            "source_height": _positive_int(source_height),
        },
        "output": (
            _sealed_output(
                state=state,
                storage_key=storage_key,
                storage_pattern=_IMAGE_STORAGE_KEY_PATTERN,
                content_type=content_type,
                byte_size=byte_size,
                sha256=sha256,
                expected_suffix=output_spec[0],
                expected_content_type=output_spec[1],
                filename=output_spec[2],
                required_positive_values=(target_width, target_height),
            )
            if output_spec is not None
            else None
        ),
    }


def _project_subtitle_asset_operation(row: tuple[Any, ...]) -> dict[str, Any]:
    """Project only bounded metadata for the strict SRT/VTT asset helper.

    A successful validation has no output by design. A conversion becomes an
    output only while its own feature gate is enabled; this keeps generic
    Jobs/Assets from advertising a private download whose typed handler is
    intentionally guarded after an operator disables the executor.
    """

    (
        record_id,
        operation_kind,
        state,
        source_format,
        target_format,
        cue_count,
        timed_duration_ms,
        storage_key,
        _filename,
        content_type,
        byte_size,
        sha256,
        semantic_sha256,
        created_at,
        queued_at,
        started_at,
        completed_at,
        updated_at,
    ) = row
    exact_state = str(state or "")
    kind = str(operation_kind or "")
    target = str(target_format or "")
    output_spec = _SUBTITLE_OUTPUT_SPECS.get(target)
    output = None
    if (
        subtitle_asset_operations_enabled()
        and kind == "subtitle_convert"
        and output_spec is not None
        and _SHA256_PATTERN.fullmatch(str(semantic_sha256 or "").lower())
        and verified_subtitle_asset_output_available(
            target_format=target,
            storage_key=storage_key,
            content_type=content_type,
            byte_size=byte_size,
            digest=sha256,
            semantic=semantic_sha256,
        )
    ):
        output = _sealed_output(
            state=state,
            storage_key=storage_key,
            storage_pattern=_SUBTITLE_STORAGE_KEY_PATTERN,
            content_type=content_type,
            byte_size=byte_size,
            sha256=sha256,
            expected_suffix=output_spec[0],
            expected_content_type=output_spec[1],
            filename=output_spec[2],
        )
    return {
        "id": encode_native_job_id("subtitle-asset-operation", record_id),
        "kind": "subtitle-asset-operation",
        "operation_kind": kind,
        "state": exact_state,
        "status": exact_state,
        "created_at": _timestamp(created_at),
        "queued_at": _timestamp(queued_at),
        "started_at": _timestamp(started_at),
        "completed_at": _timestamp(completed_at),
        "updated_at": _timestamp(updated_at),
        "summary": {
            "source_format": source_format if str(source_format or "") in _SUBTITLE_OUTPUT_SPECS else None,
            "target_format": target if target in _SUBTITLE_OUTPUT_SPECS else None,
            "cue_count": _positive_int(cue_count),
            "timed_duration_ms": _non_negative_int(timed_duration_ms),
        },
        "output": output,
    }


def _project_video_operation(row: tuple[Any, ...]) -> dict[str, Any]:
    """Project one verified Video Poster record without source identifiers."""

    (
        record_id,
        operation_kind,
        state,
        poster_position,
        source_duration_ms,
        source_width,
        source_height,
        frame_timestamp_ms,
        output_width,
        output_height,
        storage_key,
        _filename,
        content_type,
        byte_size,
        sha256,
        created_at,
        queued_at,
        started_at,
        completed_at,
        updated_at,
    ) = row
    exact_state = str(state or "")
    kind = str(operation_kind or "")
    output_spec = _VIDEO_POSTER_OUTPUT_SPEC if kind == "video_poster" else None
    return {
        "id": encode_native_job_id("video-operation", record_id),
        "kind": "video-operation",
        "operation_kind": kind,
        "state": exact_state,
        "status": exact_state,
        "created_at": _timestamp(created_at),
        "queued_at": _timestamp(queued_at),
        "started_at": _timestamp(started_at),
        "completed_at": _timestamp(completed_at),
        "updated_at": _timestamp(updated_at),
        # Do not project Asset Vault source identifiers, hashes, storage keys,
        # idempotency keys or failure details. Generic Jobs/Assets receives
        # only an opaque local job plus non-sensitive operation dimensions.
        "summary": {
            "poster_position": _safe_filename(poster_position),
            "source_duration_ms": _non_negative_int(source_duration_ms),
            "source_width": _positive_int(source_width),
            "source_height": _positive_int(source_height),
            "frame_timestamp_ms": _non_negative_int(frame_timestamp_ms),
            "output_width": _positive_int(output_width),
            "output_height": _positive_int(output_height),
        },
        "output": (
            _sealed_output(
                state=state,
                storage_key=storage_key,
                storage_pattern=_VIDEO_STORAGE_KEY_PATTERN,
                content_type=content_type,
                byte_size=byte_size,
                sha256=sha256,
                expected_suffix=output_spec[0],
                expected_content_type=output_spec[1],
                filename=output_spec[2],
                required_positive_values=(output_width, output_height),
            )
            if output_spec is not None
            else None
        ),
    }


def _project_frame_video_operation(row: tuple[Any, ...]) -> dict[str, Any]:
    """Project a sealed Frame Video receipt without source IDs or locator data."""

    (
        record_id,
        operation_kind,
        state,
        aspect_ratio,
        seconds_per_image,
        effect,
        source_count,
        source_total_bytes,
        output_duration_ms,
        output_width,
        output_height,
        storage_key,
        _filename,
        content_type,
        byte_size,
        sha256,
        created_at,
        queued_at,
        started_at,
        completed_at,
        updated_at,
    ) = row
    exact_state = str(state or "")
    kind = str(operation_kind or "")
    return {
        "id": encode_native_job_id("frame-video-operation", record_id),
        "kind": "frame-video-operation",
        "operation_kind": kind,
        "state": exact_state,
        "status": exact_state,
        "created_at": _timestamp(created_at),
        "queued_at": _timestamp(queued_at),
        "started_at": _timestamp(started_at),
        "completed_at": _timestamp(completed_at),
        "updated_at": _timestamp(updated_at),
        "summary": {
            "aspect_ratio": _safe_filename(aspect_ratio),
            "seconds_per_image": _positive_float(seconds_per_image),
            "effect": _safe_filename(effect),
            "source_count": _positive_int(source_count),
            "source_total_bytes": _non_negative_int(source_total_bytes),
            "output_duration_ms": _positive_int(output_duration_ms),
            "output_width": _positive_int(output_width),
            "output_height": _positive_int(output_height),
        },
        "output": (
            _sealed_output(
                state=state,
                storage_key=storage_key,
                storage_pattern=_FRAME_VIDEO_STORAGE_KEY_PATTERN,
                content_type=content_type,
                byte_size=byte_size,
                sha256=sha256,
                expected_suffix=_FRAME_VIDEO_OUTPUT_SPEC[0],
                expected_content_type=_FRAME_VIDEO_OUTPUT_SPEC[1],
                filename=_FRAME_VIDEO_OUTPUT_SPEC[2],
                required_positive_values=(output_duration_ms, output_width, output_height),
            )
            if kind == "frame_video"
            else None
        ),
    }


def _project_video_transform_operation(row: tuple[Any, ...]) -> dict[str, Any]:
    """Project a sealed Video Finishing receipt without source identifiers."""

    (
        record_id,
        operation_kind,
        state,
        target_ratio,
        fit_mode,
        preset,
        sharpen,
        preserve_audio,
        source_duration_ms,
        source_width,
        source_height,
        output_duration_ms,
        output_width,
        output_height,
        output_has_audio,
        storage_key,
        _filename,
        content_type,
        byte_size,
        sha256,
        created_at,
        queued_at,
        started_at,
        completed_at,
        updated_at,
    ) = row
    exact_state = str(state or "")
    kind = str(operation_kind or "")
    return {
        "id": encode_native_job_id("video-transform-operation", record_id),
        "kind": "video-transform-operation",
        "operation_kind": kind,
        "state": exact_state,
        "status": exact_state,
        "created_at": _timestamp(created_at),
        "queued_at": _timestamp(queued_at),
        "started_at": _timestamp(started_at),
        "completed_at": _timestamp(completed_at),
        "updated_at": _timestamp(updated_at),
        "summary": {
            "target_ratio": _safe_filename(target_ratio),
            "fit_mode": _safe_filename(fit_mode),
            "preset": _safe_filename(preset),
            "sharpen": bool(_integer(sharpen)),
            "preserve_audio": bool(_integer(preserve_audio)),
            "source_duration_ms": _positive_int(source_duration_ms),
            "source_width": _positive_int(source_width),
            "source_height": _positive_int(source_height),
            "output_duration_ms": _positive_int(output_duration_ms),
            "output_width": _positive_int(output_width),
            "output_height": _positive_int(output_height),
            "output_has_audio": bool(_integer(output_has_audio)) if _integer(output_has_audio) is not None else None,
        },
        "output": (
            _sealed_output(
                state=state,
                storage_key=storage_key,
                storage_pattern=_VIDEO_TRANSFORM_STORAGE_KEY_PATTERN,
                content_type=content_type,
                byte_size=byte_size,
                sha256=sha256,
                expected_suffix=_VIDEO_TRANSFORM_OUTPUT_SPEC[0],
                expected_content_type=_VIDEO_TRANSFORM_OUTPUT_SPEC[1],
                filename=_VIDEO_TRANSFORM_OUTPUT_SPEC[2],
                required_positive_values=(output_duration_ms, output_width, output_height),
            )
            if kind == "video_transform"
            else None
        ),
    }


def _project_asset(row: tuple[Any, ...]) -> dict[str, Any]:
    (
        record_id,
        display_name,
        original_filename,
        extension,
        content_type,
        byte_size,
        state,
        created_at,
        updated_at,
        archived_at,
    ) = row
    safe_filename = _safe_filename(original_filename)
    safe_name = _safe_filename(display_name) or safe_filename
    exact_state = str(state or "")
    return {
        "id": encode_native_asset_id(record_id),
        "kind": "asset",
        "name": safe_name,
        "filename": safe_filename,
        "extension": _safe_filename(extension),
        "content_type": _safe_media_type(content_type),
        "byte_size": _non_negative_int(byte_size),
        "state": exact_state,
        "status": exact_state,
        "created_at": _timestamp(created_at),
        "updated_at": _timestamp(updated_at),
        "archived_at": _timestamp(archived_at),
    }


_PACKAGE_QUERY = """
    SELECT id, state, document_count, asset_reference_count, storage_key,
           original_filename, content_type, byte_size, sha256, created_at,
           queued_at, started_at, completed_at, updated_at
      FROM web_project_packages
     WHERE account_id=?
     ORDER BY updated_at DESC, id DESC
     LIMIT ?
"""

_DOCUMENT_QUERY = """
    SELECT id, kind, state, source_count, selected_start_page,
           selected_end_page, source_page_count, output_page_count,
           storage_key, original_filename, content_type, byte_size, sha256,
           created_at, queued_at, started_at, completed_at, updated_at
      FROM web_document_operations
     WHERE account_id=?
     ORDER BY updated_at DESC, id DESC
     LIMIT ?
"""

_IMAGE_QUERY = """
    SELECT id, kind, state, target_width, target_height, preset, fit_mode,
           source_width, source_height, storage_key, original_filename,
           content_type, byte_size, sha256, created_at, queued_at, started_at,
           completed_at, updated_at
      FROM web_image_operations
     WHERE account_id=?
     ORDER BY updated_at DESC, id DESC
     LIMIT ?
"""

_SUBTITLE_ASSET_OPERATION_QUERY = """
    SELECT id, kind, state, source_format, target_format, cue_count,
           timed_duration_ms, storage_key, original_filename, content_type,
           byte_size, sha256, semantic_sha256, created_at, queued_at,
           started_at, completed_at, updated_at
      FROM web_subtitle_asset_operations
     WHERE account_id=?
     ORDER BY updated_at DESC, id DESC
     LIMIT ?
"""

_VIDEO_QUERY = """
    SELECT id, kind, state, poster_position, source_duration_ms,
           source_width, source_height, frame_timestamp_ms, output_width,
           output_height, storage_key, original_filename, content_type,
           byte_size, sha256, created_at, queued_at, started_at, completed_at,
           updated_at
      FROM web_video_operations
     WHERE account_id=? AND kind='video_poster'
     ORDER BY updated_at DESC, id DESC
     LIMIT ?
"""

_FRAME_VIDEO_QUERY = """
    SELECT id, kind, state, aspect_ratio, seconds_per_image, effect,
           source_count, source_total_bytes, output_duration_ms, output_width,
           output_height, storage_key, original_filename, content_type,
           byte_size, sha256, created_at, queued_at, started_at, completed_at,
           updated_at
      FROM web_frame_video_operations
     WHERE account_id=? AND kind='frame_video'
     ORDER BY updated_at DESC, id DESC
     LIMIT ?
"""

_VIDEO_TRANSFORM_QUERY = """
    SELECT id, kind, state, target_ratio, fit_mode, preset, sharpen,
           preserve_audio, source_duration_ms, source_width, source_height,
           output_duration_ms, output_width, output_height, output_has_audio,
           storage_key, original_filename, content_type, byte_size, sha256,
           created_at, queued_at, started_at, completed_at, updated_at
      FROM web_video_transform_operations
     WHERE account_id=? AND kind='video_transform'
     ORDER BY updated_at DESC, id DESC
     LIMIT ?
"""

_ASSET_QUERY = """
    SELECT id, display_name, original_filename, extension, content_type,
           byte_size, state, created_at, updated_at, archived_at
      FROM web_asset_files
     WHERE account_id=?
     ORDER BY updated_at DESC, id DESC
     LIMIT ?
"""

_PACKAGE_COMPLETED_QUERY = _PACKAGE_QUERY.replace("WHERE account_id=?", "WHERE account_id=? AND state='completed'")
_DOCUMENT_COMPLETED_QUERY = _DOCUMENT_QUERY.replace("WHERE account_id=?", "WHERE account_id=? AND state='completed'")
_IMAGE_COMPLETED_QUERY = _IMAGE_QUERY.replace("WHERE account_id=?", "WHERE account_id=? AND state='completed'")
_SUBTITLE_ASSET_OPERATION_COMPLETED_QUERY = _SUBTITLE_ASSET_OPERATION_QUERY.replace(
    "WHERE account_id=?", "WHERE account_id=? AND state='completed'"
)
_VIDEO_COMPLETED_QUERY = _VIDEO_QUERY.replace(
    "WHERE account_id=? AND kind='video_poster'",
    "WHERE account_id=? AND kind='video_poster' AND state='completed'",
)
_FRAME_VIDEO_COMPLETED_QUERY = _FRAME_VIDEO_QUERY.replace(
    "WHERE account_id=? AND kind='frame_video'",
    "WHERE account_id=? AND kind='frame_video' AND state='completed'",
)
_VIDEO_TRANSFORM_COMPLETED_QUERY = _VIDEO_TRANSFORM_QUERY.replace(
    "WHERE account_id=? AND kind='video_transform'",
    "WHERE account_id=? AND kind='video_transform' AND state='completed'",
)


def _projected_jobs_for_account(
    conn: Any,
    account_id: str,
    limit: int,
    *,
    completed_outputs_only: bool = False,
) -> list[dict[str, Any]]:
    """Read each supported source through static SQL, then merge safely."""

    sortable: list[tuple[str, str, str, dict[str, Any]]] = []
    sources: list[tuple[str, str, Any]] = [
        (
            "project-package",
            _PACKAGE_COMPLETED_QUERY if completed_outputs_only else _PACKAGE_QUERY,
            _project_package,
        ),
        (
            "document-operation",
            _DOCUMENT_COMPLETED_QUERY if completed_outputs_only else _DOCUMENT_QUERY,
            _project_document_operation,
        ),
        (
            "image-operation",
            _IMAGE_COMPLETED_QUERY if completed_outputs_only else _IMAGE_QUERY,
            _project_image_operation,
        ),
        (
            "video-operation",
            _VIDEO_COMPLETED_QUERY if completed_outputs_only else _VIDEO_QUERY,
            _project_video_operation,
        ),
    ]
    # The read model never creates schema. When this optional executor is
    # disabled, skip its table completely so a pre-feature database remains a
    # safe read-only source for the already-enabled generic Jobs/Assets page.
    if subtitle_asset_operations_enabled():
        sources.append(
            (
                "subtitle-asset-operation",
                _SUBTITLE_ASSET_OPERATION_COMPLETED_QUERY if completed_outputs_only else _SUBTITLE_ASSET_OPERATION_QUERY,
                _project_subtitle_asset_operation,
            )
        )
    if frame_video_operations_enabled():
        sources.append(
            (
                "frame-video-operation",
                _FRAME_VIDEO_COMPLETED_QUERY if completed_outputs_only else _FRAME_VIDEO_QUERY,
                _project_frame_video_operation,
            )
        )
    if video_transform_operations_enabled():
        sources.append(
            (
                "video-transform-operation",
                _VIDEO_TRANSFORM_COMPLETED_QUERY if completed_outputs_only else _VIDEO_TRANSFORM_QUERY,
                _project_video_transform_operation,
            )
        )
    for source, query, projector in sources:
        for row in conn.execute(query, (account_id, limit)).fetchall():
            values = tuple(row)
            try:
                job = projector(values)
            except ValueError:
                # A malformed legacy row must not make unrelated owner data
                # disappear or create an over-length route identifier.
                continue
            if completed_outputs_only and not isinstance(job.get("output"), dict):
                continue
            # Raw IDs exist only long enough to make tied timestamps stable;
            # they are never placed in a public dict.
            sortable.append((str(values[-1] or ""), source, str(values[0]), job))
    sortable.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return [item[3] for item in sortable[:limit]]


def list_native_jobs(account_id: str, *, limit: int = MAX_LIST_LIMIT) -> list[dict[str, Any]]:
    """Return at most 100 owner-scoped generic Web-native job projections.

    The query is intentionally read-only.  It does not call
    ``ensure_copyfast_schema`` because schema setup is a write and belongs to
    application startup, not to a read model.
    """

    owner_id = _account_id(account_id)
    if not owner_id:
        return []
    bounded_limit = _bounded_limit(limit)
    with read_transaction() as conn:
        return _projected_jobs_for_account(conn, owner_id, bounded_limit)


def list_native_completed_outputs(account_id: str, *, limit: int = MAX_LIST_LIMIT) -> list[dict[str, Any]]:
    """Return bounded completed jobs with sealed-output metadata only.

    This deliberately queries completed rows separately from ``list_native_jobs``
    so a full page of newer queued/processing rows cannot hide a usable local
    output from the generic Assets projection.
    """

    owner_id = _account_id(account_id)
    if not owner_id:
        return []
    bounded_limit = _bounded_limit(limit)
    with read_transaction() as conn:
        return _projected_jobs_for_account(
            conn,
            owner_id,
            bounded_limit,
            completed_outputs_only=True,
        )


def resolve_native_job(conn: Any, account_id: str, public_id: str) -> dict[str, Any] | None:
    """Resolve one owner-scoped opaque job using an existing DB connection.

    Write-side coordination modules use this helper inside their own SQLite
    transaction so reference validation cannot be split into a separate
    read/validate phase.  It still only projects safe metadata and never
    reads a blob, calls a provider, or exposes a decoded internal identifier.
    """

    owner_id = _account_id(account_id)
    parsed = parse_native_job_id(public_id)
    if not owner_id or parsed is None:
        return None
    source, internal_id = parsed
    if source == "subtitle-asset-operation" and not subtitle_asset_operations_enabled():
        return None
    if source == "frame-video-operation" and not frame_video_operations_enabled():
        return None
    if source == "video-transform-operation" and not video_transform_operations_enabled():
        return None
    queries: dict[str, tuple[str, Any]] = {
        "project-package": (_PACKAGE_QUERY, _project_package),
        "document-operation": (_DOCUMENT_QUERY, _project_document_operation),
        "image-operation": (_IMAGE_QUERY, _project_image_operation),
        "subtitle-asset-operation": (_SUBTITLE_ASSET_OPERATION_QUERY, _project_subtitle_asset_operation),
        "video-operation": (_VIDEO_QUERY, _project_video_operation),
        "frame-video-operation": (_FRAME_VIDEO_QUERY, _project_frame_video_operation),
        "video-transform-operation": (_VIDEO_TRANSFORM_QUERY, _project_video_transform_operation),
    }
    query_and_projector = queries.get(source)
    if query_and_projector is None:
        return None
    query, projector = query_and_projector
    row = conn.execute(
        query.replace("WHERE account_id=?", "WHERE account_id=? AND id=?"),
        (owner_id, internal_id, 1),
    ).fetchone()
    if not row:
        return None
    try:
        return projector(tuple(row))
    except ValueError:
        # A legacy row that cannot form a route-safe opaque ID is never a
        # valid reference target, and must not turn into a 500/error oracle.
        return None


def get_native_job(account_id: str, public_id: str) -> dict[str, Any] | None:
    """Return one owner-scoped job projection, or ``None`` for missing/unknown IDs."""

    with read_transaction() as conn:
        return resolve_native_job(conn, account_id, public_id)


def resolve_native_asset(conn: Any, account_id: str, public_id: str) -> dict[str, Any] | None:
    """Resolve one owner-scoped opaque Asset Vault projection in one transaction."""

    owner_id = _account_id(account_id)
    internal_id = parse_native_asset_id(public_id)
    if not owner_id or internal_id is None:
        return None
    row = conn.execute(
        _ASSET_QUERY.replace("WHERE account_id=?", "WHERE account_id=? AND id=?"),
        (owner_id, internal_id, 1),
    ).fetchone()
    if not row:
        return None
    try:
        return _project_asset(tuple(row))
    except ValueError:
        return None


def get_native_asset(account_id: str, public_id: str) -> dict[str, Any] | None:
    """Return one owner-scoped Asset Vault projection without a write transaction."""

    with read_transaction() as conn:
        return resolve_native_asset(conn, account_id, public_id)


def list_native_assets(account_id: str, *, limit: int = MAX_LIST_LIMIT) -> list[dict[str, Any]]:
    """Return at most 100 owner-scoped Asset Vault metadata projections."""

    owner_id = _account_id(account_id)
    if not owner_id:
        return []
    bounded_limit = _bounded_limit(limit)
    with read_transaction() as conn:
        rows = conn.execute(_ASSET_QUERY, (owner_id, bounded_limit)).fetchall()
    assets: list[dict[str, Any]] = []
    for row in rows:
        try:
            assets.append(_project_asset(tuple(row)))
        except ValueError:
            continue
    return assets
