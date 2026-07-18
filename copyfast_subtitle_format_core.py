"""Strict, deterministic SRT/VTT parsing and rendering for private artifacts.

The caption studio owns author-entered text and deliberately keeps its own
compatible import behaviour.  This small core is for the stricter Asset Vault
operation boundary: it accepts only a safe, portable subset of SRT/VTT and
never interprets markup, metadata, URLs, media, providers or filesystem paths.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Iterable


SUPPORTED_FORMATS = frozenset({"srt", "vtt"})
MAX_INPUT_BYTES = 96 * 1024
MAX_OUTPUT_BYTES = 96 * 1024
MAX_CUES = 500
MAX_CUE_CHARACTERS = 5_000
MAX_DURATION_MS = 24 * 60 * 60 * 1_000

_SRT_TIMING = re.compile(
    r"^(?P<start>\d{1,2}:\d{2}:\d{2},\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2},\d{3})$"
)
_VTT_TIMING = re.compile(
    r"^(?P<start>(?:\d{1,2}:)?\d{2}:\d{2}\.\d{3})\s*-->\s*"
    r"(?P<end>(?:\d{1,2}:)?\d{2}:\d{2}\.\d{3})$"
)
_VTT_UNSUPPORTED_BLOCK = re.compile(r"^(?:NOTE|STYLE|REGION)(?:\s|$)", re.IGNORECASE)
_DANGEROUS_CAPTION_TOKEN = re.compile(r"(?:<\s*script\b|javascript\s*:|data\s*:\s*text/html)", re.IGNORECASE)


class SubtitleFormatError(ValueError):
    """A safe, public validation failure for a private subtitle artifact."""


@dataclass(frozen=True)
class SubtitleCue:
    """One plain-text caption interval represented only with integer ms."""

    start_ms: int
    end_ms: int
    text: str


def _require_format(value: str) -> str:
    fmt = str(value or "").strip().lower()
    if fmt not in SUPPORTED_FORMATS:
        raise SubtitleFormatError("Chỉ hỗ trợ định dạng SRT hoặc VTT")
    return fmt


def decode_subtitle_bytes(value: bytes) -> str:
    """Decode one bounded UTF-8/UTF-8-BOM Asset Vault payload safely."""

    if not isinstance(value, bytes) or not value:
        raise SubtitleFormatError("Tệp subtitle không có nội dung")
    if len(value) > MAX_INPUT_BYTES:
        raise SubtitleFormatError("Tệp subtitle vượt giới hạn 96 KiB")
    try:
        text = value.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SubtitleFormatError("Tệp subtitle phải dùng UTF-8") from exc
    return _normalise_text(text)


def _normalise_text(value: str) -> str:
    if not isinstance(value, str):
        raise SubtitleFormatError("Nội dung subtitle không hợp lệ")
    encoded = value.encode("utf-8")
    if len(encoded) > MAX_INPUT_BYTES:
        raise SubtitleFormatError("Tệp subtitle vượt giới hạn 96 KiB")
    if value.startswith("\ufeff"):
        value = value[1:]
    for character in value:
        codepoint = ord(character)
        if (codepoint < 32 and character not in {"\n", "\r", "\t"}) or 0x7F <= codepoint <= 0x9F:
            raise SubtitleFormatError("Tệp subtitle có ký tự điều khiển không an toàn")
    normalised = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalised:
        raise SubtitleFormatError("Tệp subtitle không có nội dung")
    return normalised


def _timestamp(value: str, *, fmt: str) -> int:
    candidate = str(value or "").strip()
    if fmt == "srt":
        matched = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2}),(\d{3})", candidate)
    else:
        matched = re.fullmatch(r"(?:(\d{1,2}):)?(\d{2}):(\d{2})\.(\d{3})", candidate)
    if not matched:
        raise SubtitleFormatError("Mốc thời gian subtitle không hợp lệ")
    groups = matched.groups()
    if fmt == "srt":
        hours, minutes, seconds, milliseconds = (int(item) for item in groups)
    else:
        hours = int(groups[0] or 0)
        minutes, seconds, milliseconds = (int(item) for item in groups[1:])
    if minutes >= 60 or seconds >= 60:
        raise SubtitleFormatError("Mốc thời gian subtitle không hợp lệ")
    result = (((hours * 60 + minutes) * 60 + seconds) * 1_000) + milliseconds
    if result > MAX_DURATION_MS:
        raise SubtitleFormatError("Subtitle chỉ hỗ trợ timeline tối đa 24 giờ")
    return result


def _caption_text(lines: list[str]) -> str:
    if not lines:
        raise SubtitleFormatError("Mỗi cue subtitle phải có nội dung")
    # Preserve plain caption line breaks while avoiding invisible trailing
    # spacing becoming a second semantic representation of the same artifact.
    text = "\n".join(line.rstrip() for line in lines).strip()
    if not text:
        raise SubtitleFormatError("Mỗi cue subtitle phải có nội dung")
    if len(text) > MAX_CUE_CHARACTERS:
        raise SubtitleFormatError("Một cue subtitle vượt giới hạn 5.000 ký tự")
    if _DANGEROUS_CAPTION_TOKEN.search(text):
        raise SubtitleFormatError("Cue subtitle chứa markup hoặc URI không an toàn")
    return text


def parse_subtitle_text(fmt: str, value: str) -> tuple[SubtitleCue, ...]:
    """Parse only the portable, metadata-free SRT/VTT cue subset.

    The operation does not silently discard VTT style/region/note/configuration
    blocks because doing so could turn a semantically different file into a
    completed private artifact.  VTT cue identifiers and timing settings are
    intentionally unsupported.  SRT's required numeric sequence line is
    accepted only when it is canonical (1, 2, 3, ...) so the parser accepts
    normal SRT while never turning an arbitrary identifier into caption data.
    Conversion is therefore transparent: timestamps/container normalise,
    caption text does not change.
    """

    normalized_format = _require_format(fmt)
    text = _normalise_text(value)
    if normalized_format == "vtt":
        lines = text.split("\n")
        if not lines or lines[0].strip() != "WEBVTT":
            raise SubtitleFormatError("VTT phải bắt đầu bằng WEBVTT")
        if len(lines) > 1 and lines[1].strip():
            raise SubtitleFormatError("VTT header metadata chưa được hỗ trợ")
        text = "\n".join(lines[1:]).strip()
        if not text:
            raise SubtitleFormatError("Không tìm thấy cue VTT hợp lệ")

    pattern = _VTT_TIMING if normalized_format == "vtt" else _SRT_TIMING
    blocks = [block.strip() for block in re.split(r"\n[ \t]*\n", text) if block.strip()]
    cues: list[SubtitleCue] = []
    previous_end = -1
    for block in blocks:
        lines = [line.rstrip() for line in block.split("\n")]
        if normalized_format == "vtt" and lines and _VTT_UNSUPPORTED_BLOCK.match(lines[0].strip()):
            raise SubtitleFormatError("VTT NOTE, STYLE và REGION chưa được hỗ trợ cho file private")
        if not lines:
            continue
        timing_index = 0
        if normalized_format == "srt" and len(lines) >= 2:
            sequence = lines[0].strip()
            if re.fullmatch(r"[0-9]+", sequence):
                if sequence != str(len(cues) + 1):
                    raise SubtitleFormatError("Số thứ tự cue SRT không hợp lệ")
                timing_index = 1
        timing = pattern.fullmatch(lines[timing_index].strip())
        if not timing:
            raise SubtitleFormatError("Cue subtitle phải bắt đầu bằng dòng thời gian hợp lệ, không có identifier hoặc setting")
        start_ms = _timestamp(timing.group("start"), fmt=normalized_format)
        end_ms = _timestamp(timing.group("end"), fmt=normalized_format)
        if end_ms <= start_ms:
            raise SubtitleFormatError("Thời điểm kết thúc cue phải sau thời điểm bắt đầu")
        if start_ms < previous_end:
            raise SubtitleFormatError("Các cue subtitle không được chồng thời gian")
        # A second timing line without a blank separator would otherwise be
        # preserved as caption text and silently collapse two cues into one.
        # The private converter must reject that ambiguous source instead of
        # claiming a semantically faithful conversion.
        if any(pattern.fullmatch(line.strip()) for line in lines[timing_index + 1 :]):
            raise SubtitleFormatError("Các cue subtitle phải được phân tách bằng một dòng trống")
        caption = _caption_text(lines[timing_index + 1 :])
        cues.append(SubtitleCue(start_ms=start_ms, end_ms=end_ms, text=caption))
        previous_end = end_ms
        if len(cues) > MAX_CUES:
            raise SubtitleFormatError(f"Tệp subtitle tối đa {MAX_CUES} cues")
    if not cues:
        raise SubtitleFormatError("Không tìm thấy cue subtitle hợp lệ")
    return tuple(cues)


def _format_timestamp(value: int, *, fmt: str) -> str:
    total = int(value)
    if total < 0 or total > MAX_DURATION_MS:
        raise SubtitleFormatError("Mốc thời gian subtitle không hợp lệ")
    hours, remainder = divmod(total, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    separator = "." if fmt == "vtt" else ","
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{milliseconds:03d}"


def render_subtitle_text(fmt: str, cues: Iterable[SubtitleCue]) -> str:
    """Render canonical UTF-8 text and reassert all semantic bounds."""

    normalized_format = _require_format(fmt)
    materialized = tuple(cues)
    if not materialized or len(materialized) > MAX_CUES:
        raise SubtitleFormatError("Số cue subtitle không hợp lệ")
    lines: list[str] = ["WEBVTT", ""] if normalized_format == "vtt" else []
    previous_end = -1
    for index, cue in enumerate(materialized, start=1):
        if not isinstance(cue, SubtitleCue):
            raise SubtitleFormatError("Cue subtitle không hợp lệ")
        if cue.end_ms <= cue.start_ms or cue.start_ms < previous_end:
            raise SubtitleFormatError("Timeline subtitle không hợp lệ")
        caption = _caption_text(cue.text.split("\n"))
        if normalized_format == "srt":
            lines.append(str(index))
        lines.append(
            f"{_format_timestamp(cue.start_ms, fmt=normalized_format)} --> "
            f"{_format_timestamp(cue.end_ms, fmt=normalized_format)}"
        )
        lines.append(caption)
        lines.append("")
        previous_end = cue.end_ms
    rendered = "\n".join(lines).rstrip() + "\n"
    if len(rendered.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise SubtitleFormatError("Output subtitle vượt giới hạn 96 KiB")
    return rendered


def cues_digest(cues: Iterable[SubtitleCue]) -> str:
    """Hash semantic cues, not an input container or filesystem name."""

    canonical = json.dumps(
        [
            {"start_ms": cue.start_ms, "end_ms": cue.end_ms, "text": cue.text}
            for cue in tuple(cues)
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
