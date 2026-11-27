"""Finite AGC source inverse for historical QA only, never application runtime."""

import hashlib
import json
from pathlib import Path
import re


_FAIL = "Unreviewed Admin guard customer copy history"
_TARGETS = {"static/portal/portal.js", "static/portal/portal-i18n.js"}
_RAW = (Path(__file__).resolve().parents[1] / "fixtures/admin-guard-customer-copy-history.json").read_bytes().decode("utf-8").replace("\r\n", "\n")


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(f"{_FAIL}: {detail}")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


_require(_hash(_RAW) == "85dc5ee00b8cb42ec670ec782dbacca6e61d4f33b5436a1d9675b461770f8080", "fixture hash")
_FIXTURE = json.loads(_RAW)
_require(_FIXTURE["base_sha"] == "5f316f29c9b8657c4018f5174c4c4ce4f16c1e5f", "BASE")
_require(len(_FIXTURE["records"]) == 22 and len(_FIXTURE["owners"]) == 5, "record/owner count")
_require([row["conversation_id"] for row in _FIXTURE["provenance"]] == [
    "9dbcc5de-90b9-4a79-9a07-d1e98831c3f3",
    "dac917b7-aadc-4c2a-b14b-c6866ccbcf8d",
    "fab6a78b-c666-4cc9-ae63-a8e2c20576aa",
], "provenance")
for _row in [*_FIXTURE["records"], *_FIXTURE["owners"]]:
    _require(_row["file"] in _TARGETS and isinstance(_row["before"], str)
             and isinstance(_row["after"], str), "record shape/target")
    _require(_hash(_row["before"]) == _row["before_lf_sha256"], "before hash")
    _require(_hash(_row["after"]) == _row["after_lf_sha256"], "after hash")
_INSERTION = next(row for row in _FIXTURE["owners"] if row["slot"]["kind"] == "insertion")
_ACTION_KEYS = list(dict.fromkeys(re.findall(r'"(actionBlockReason\.[^"]+)"\s*:', _INSERTION["after"])))
_require(bool(_ACTION_KEYS), "action keys")
_ACTION_DECLARATIONS = re.compile(r'"(' + "|".join(re.escape(key) for key in _ACTION_KEYS) + r')"\s*:')
_PORTAL_SIGNAL = re.compile(r'uiText\("actionBlockReason\.')


def _once(source: str, part: str, label: str) -> int:
    _require(isinstance(part, str) and bool(part), f"nonempty {label}")
    _require(source.count(part) == 1, f"unique {label}")
    return source.index(part)


def _context_gap(gap: str) -> None:
    """Inspect only the finite owner gap; comments/quoted text are not code."""
    code, mode, escaped, index = [], "", False, 0
    while index < len(gap):
        char = gap[index]
        following = gap[index + 1] if index + 1 < len(gap) else ""
        if mode == "line":
            code.append("\n" if char == "\n" else " ")
            if char == "\n":
                mode = ""
        elif mode == "block":
            if char == "*" and following == "/":
                code.append("  ")
                index += 1
                mode = ""
            else:
                code.append("\n" if char == "\n" else " ")
        elif mode:
            code.append("\n" if char == "\n" else " ")
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == mode:
                mode = ""
        elif char == "/" and following == "/":
            code.append("  ")
            index += 1
            mode = "line"
        elif char == "/" and following == "*":
            code.append("  ")
            index += 1
            mode = "block"
        elif char in "\"'`":
            code.append(" ")
            mode = char
        else:
            code.append(char)
        index += 1
    _require(mode in ("", "line"), "closed slot comments/strings")
    text = "".join(code)
    _require(not re.search(r"^  (?:async[ \t]+)?(?:function|const|let|class)\b", text, re.MULTILINE),
             "no intervening slot declaration")
    stack, opening, closing = [], "([{", ")]}"
    for char in text:
        if char in opening:
            stack.append(char)
        elif char in closing:
            _require(bool(stack) and stack.pop() == opening[closing.index(char)], "balanced slot context")
    _require(not stack, "no foreign enclosing block")


def _slot(source: str, row: dict) -> tuple[int, int]:
    start = _once(source, row["after"], row["name"])
    stop = start + len(row["after"])
    slot = row["slot"]
    previous = _once(source, slot["previous"], row["name"] + " previous owner")
    following = _once(source, slot["following"], row["name"] + " following owner")
    _once(source, slot["declaration"], row["name"] + " declaration")
    lower = previous + len(slot["previous"])
    if slot["kind"] == "function":
        previous_end = source.find("\n  }\n", previous)
        _require(previous_end > previous, "closed previous function")
        lower = previous_end + 5
    else:
        _require(slot["kind"] in {"array", "insertion"}, "known slot")
    _require(lower <= start < stop <= following, "owner slot/order")
    _context_gap(source[lower:start])
    if slot["kind"] == "insertion":
        declarations = _ACTION_DECLARATIONS.findall(source)
        for key in _ACTION_KEYS:
            _require(declarations.count(key) == 3, "action declaration ownership")
    return start, stop


def admin_guard_customer_copy_historical_source(source: str, file: str) -> str:
    """Reverse only the approved AGC deltas, retaining all bytes outside owners."""
    _require(isinstance(source, str), "string source")
    if file not in _TARGETS:
        return source
    owners = [row for row in _FIXTURE["owners"] if row["file"] == file]
    records = [row for row in _FIXTURE["records"] if row["file"] == file]
    has_signal = (
        (file == "static/portal/portal.js" and bool(_PORTAL_SIGNAL.search(source)))
        or any(row["after"] and row["after"] in source for row in records)
        or any(row["after"] in source for row in owners)
    )
    if not has_signal:
        return source
    previous_stop, ranges = -1, []
    for row in owners:
        start, stop = _slot(source, row)
        _require(start >= previous_stop, "file owner order")
        previous_stop = stop
        ranges.append((start, stop))
    for row in records:
        if not row["after"]:
            continue
        start = _once(source, row["after"], "approved proposal record")
        _require(any(lower <= start and start + len(row["after"]) <= upper
                     for lower, upper in ranges), "record ownership")
    for row in reversed(owners):
        _once(source, row["after"], "approved owner inverse")
        source = source.replace(row["after"], row["before"], 1)
    return source
