"""Exact Gallery transport inverse for historical QA inputs, never app runtime."""

import hashlib
import json
from pathlib import Path
import re
from tests.helpers.auth_return_historical import auth_return_historical_source


_FAIL = "Unreviewed Gallery native transport history"
_TARGET = "static/portal/integration.js"
_RAW = (Path(__file__).resolve().parents[1] / "fixtures/gallery-native-transport-history.json").read_bytes().decode("utf-8").replace("\r\n", "\n")


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(f"{_FAIL}: {detail}")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


_require(_hash(_RAW) == "70194054446d00266cd8d0c692d668588a29d4dcb23cdbf647e7c74cfd141d05", "fixture hash")
_FIXTURE = json.loads(_RAW)
_require(_FIXTURE["base_sha"] == "29e0c154dfd247ac4b0a68cd6336ec83fb3af8ef", "BASE")
_require(_FIXTURE["file"] == _TARGET and len(_FIXTURE["records"]) == 11, "eleven target records")
_RECORDS = _FIXTURE["records"]
for _row in _RECORDS:
    _require(_row["file"] == _TARGET, "record target")
    _require(_hash(_row["before"]) == _row["before_lf_sha256"], "before hash")
    _require(_hash(_row["after"]) == _row["after_lf_sha256"], "after hash")

_FUNCTION = re.compile(r"^  (?:async )?function [A-Za-z_][A-Za-z0-9_]*\(", re.MULTILINE)
_SIGNALS = re.compile(
    r"^[ \t]*(?:let freePromptGalleryLocaleOwner[ \t]*=|const freePromptGalleryActionEpochs[ \t]*=|const FREE_PROMPT_GALLERY_FEEDBACK_VI[ \t]*=)"
    r"|freePromptGalleryCreateError\(|freePromptGalleryActiveLocale\("
    r"|function freePromptGalleryItemsPath\(filter, page, locale\)",
    re.MULTILINE,
)


def _once(source: str, part: str, label: str) -> int:
    _require(source.count(part) == 1, f"unique {label}")
    return source.index(part)


def _end(source: str, start: int, closing: str, label: str) -> int:
    end = source.find(closing, start)
    _require(end > start, f"closed {label}")
    return end + len(closing)


def _slot(source: str, row: dict) -> None:
    """Validate finite owner markers and the existing indentation boundaries."""
    start = _once(source, row["after"], "approved after")
    stop = start + len(row["after"])
    slot = row["slot"]
    previous = _once(source, slot["previous"], "previous slot owner")
    following = _once(source, slot["following"], "following slot owner")
    if slot["kind"] == "function":
        lower = _end(source, previous, "\n  }\n", "previous function")
    elif slot["kind"] == "action":
        lower = _end(source, previous, "\n      }\n", "previous action")
        owner = _once(source, "  async function handleAction(event) {", "handleAction owner")
        owner_end = _end(source, owner, "\n  }\n", "handleAction")
        _require(owner < start < stop < owner_end, "action inside handleAction")
        _once(source, row["after"].splitlines()[0], "action branch")
    else:
        _require(slot["kind"] == "state", "known slot kind")
        lower = previous + len(slot["previous"])
        _once(source, row["after"].splitlines()[0], "state declaration")
    _require(lower <= start < stop <= following, "record slot/order")
    for marker in _FUNCTION.findall(row["after"]):
        _once(source, marker, "function declaration owner")


def gallery_native_transport_historical_source(
    source: str, file: str = _TARGET
) -> str:
    """Reverse only all eleven approved Gallery edits; preserve other bytes."""
    _require(isinstance(source, str), "string source")
    source = auth_return_historical_source(source, file)
    if file != _TARGET or not _SIGNALS.search(source):
        return source
    for row in reversed(_RECORDS):
        _slot(source, row)
        source = source.replace(row["after"], row["before"], 1)
    return source
