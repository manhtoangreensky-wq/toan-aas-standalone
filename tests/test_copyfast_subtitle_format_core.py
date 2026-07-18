"""Focused contract tests for the strict private SRT/VTT codec.

The authoring studio deliberately supports a broader, user-friendly import
surface.  These tests instead protect the narrower Asset Vault boundary: a
conversion must preserve caption semantics, and unsupported metadata or unsafe
input must be rejected rather than silently discarded.
"""

from __future__ import annotations

import pytest

from copyfast_subtitle_format_core import (
    SubtitleFormatError,
    cues_digest,
    decode_subtitle_bytes,
    parse_subtitle_text,
    render_subtitle_text,
)


def test_strict_codec_converts_srt_to_canonical_vtt_without_changing_cues() -> None:
    source = (
        "1\n"
        "00:00:01,000 --> 00:00:02,400\n"
        "Xin chào\n\n"
        "2\n"
        "00:00:02,400 --> 00:00:03,000\n"
        "Dòng thứ hai\n"
        "vẫn thuộc cùng cue\n"
    )

    source_cues = parse_subtitle_text("srt", source)
    rendered_vtt = render_subtitle_text("vtt", source_cues)
    restored_cues = parse_subtitle_text("vtt", rendered_vtt)

    assert rendered_vtt == (
        "WEBVTT\n\n"
        "00:00:01.000 --> 00:00:02.400\n"
        "Xin chào\n\n"
        "00:00:02.400 --> 00:00:03.000\n"
        "Dòng thứ hai\n"
        "vẫn thuộc cùng cue\n"
    )
    assert restored_cues == source_cues
    assert cues_digest(restored_cues) == cues_digest(source_cues)


def test_strict_codec_accepts_utf8_bom_but_rejects_non_utf8_and_control_bytes() -> None:
    decoded = decode_subtitle_bytes(
        b"\xef\xbb\xbfWEBVTT\n\n00:00.000 --> 00:01.000\nXin chao\n"
    )

    assert parse_subtitle_text("vtt", decoded)[0].text == "Xin chao"

    with pytest.raises(SubtitleFormatError, match="UTF-8"):
        decode_subtitle_bytes(b"\xff\xfe\x00")
    with pytest.raises(SubtitleFormatError, match="ký tự điều khiển"):
        decode_subtitle_bytes(b"1\n00:00:00,000 --> 00:00:01,000\nXin\x00chao")


@pytest.mark.parametrize(
    ("fmt", "source", "message"),
    [
        (
            "srt",
            "1\n00:00:00,000 - 00:00:01,000\nThiếu mũi tên",
            "dòng thời gian hợp lệ",
        ),
        (
            "vtt",
            "WEBVTT\nKind: captions\n\n00:00.000 --> 00:01.000\nMetadata",
            "header metadata",
        ),
        (
            "vtt",
            "WEBVTT\n\nSTYLE\n::cue { color: red; }\n\n00:00.000 --> 00:01.000\nNội dung",
            "NOTE, STYLE và REGION",
        ),
        (
            "vtt",
            "WEBVTT\n\n00:00.000 --> 00:01.000 align:start\nKhông hỗ trợ setting",
            "identifier hoặc setting",
        ),
    ],
)
def test_strict_codec_rejects_malformed_or_metadata_bearing_vtt_and_srt(
    fmt: str, source: str, message: str
) -> None:
    with pytest.raises(SubtitleFormatError, match=message):
        parse_subtitle_text(fmt, source)


def test_strict_codec_rejects_overlapping_timeline() -> None:
    source = (
        "WEBVTT\n\n"
        "00:00.000 --> 00:02.000\nCue đầu\n\n"
        "00:01.999 --> 00:03.000\nCue chồng thời gian"
    )

    with pytest.raises(SubtitleFormatError, match="chồng thời gian"):
        parse_subtitle_text("vtt", source)


def test_strict_codec_rejects_cues_without_a_blank_separator() -> None:
    source = (
        "WEBVTT\n\n"
        "00:00.000 --> 00:01.000\nCue một\n"
        "00:01.000 --> 00:02.000\nCue hai"
    )

    with pytest.raises(SubtitleFormatError, match="phân tách"):
        parse_subtitle_text("vtt", source)


def test_strict_codec_requires_canonical_srt_sequence_numbers() -> None:
    with pytest.raises(SubtitleFormatError, match="Số thứ tự cue"):
        parse_subtitle_text("srt", "01\n00:00:00,000 --> 00:00:01,000\nKhông canonical")


@pytest.mark.parametrize(
    "caption",
    [
        "<script>alert('x')</script>",
        "javascript:alert('x')",
        "data:text/html;base64,PHNjcmlwdD4=",
    ],
)
def test_strict_codec_rejects_dangerous_caption_markup_or_uri(caption: str) -> None:
    source = f"WEBVTT\n\n00:00.000 --> 00:01.000\n{caption}"

    with pytest.raises(SubtitleFormatError, match="không an toàn"):
        parse_subtitle_text("vtt", source)
