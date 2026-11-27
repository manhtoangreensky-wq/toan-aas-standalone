"""Finite auth-return inverse for historical QA inputs only; never app runtime."""
import hashlib
import json
from pathlib import Path
import re

_FAIL = "Unreviewed auth return history"
_RAW = (Path(__file__).resolve().parents[1] / "fixtures/auth-return-history.json").read_bytes().decode().replace("\r\n", "\n")


def _require(value: bool, label: str) -> None:
    if not value:
        raise ValueError(f"{_FAIL}: {label}")


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


_require(_sha(_RAW) == "97a8aad3f4b8a0251a80222c7e5af4fe27b1b49e6d1cbfd2dd4f6d19797dfae3", "fixture hash")
_FIXTURE = json.loads(_RAW)
_require(_FIXTURE["base_sha"] == "fc9aef439d8fe7ecb00a2c68a167dad501f54eb9" and len(_FIXTURE["records"]) == 2, "BASE/count")
_require([row["file"] for row in _FIXTURE["records"]] == ["static/portal/portal-auth.js", "static/portal/integration.js"], "exact targets")
for _row in _FIXTURE["records"]:
    _require(all(_sha(_row[name]) == _row[name + "_sha256"] for name in ("before", "after")), "record hashes")
_SIGNALS = (r"/[\u0000-\u001f\u007f]/.test(route)", 'normalized === "/api"', 'normalized === "/internal"', 'normalized.includes("%")')
_DECLARATION = re.compile(r"\bfunction\s+safeReturnPath\s*\(")
_OWNER = re.compile(r"^  (?:async )?function [A-Za-z_][A-Za-z0-9_]*\(", re.MULTILINE)


def auth_return_historical_source(source: str, file: str) -> str:
    """Reverse one exact owned helper, preserving every byte outside it."""
    _require(isinstance(source, str), "string source")
    row = next((row for row in _FIXTURE["records"] if row["file"] == file), None)
    if row is None or not any(signal in source for signal in _SIGNALS):
        return source
    variants = [(row["after"].replace("\n", ending), row["before"].replace("\n", ending))
                for ending in ("\n", "\r\n")]
    matches = [(after, before) for after, before in variants if after in source]
    _require(len(matches) == 1, "one exact complete helper")
    after, before = matches[0]
    _require(source.count(after) == 1 and len(_DECLARATION.findall(source)) == 1, "unique helper owner")
    _require(source.count(row["previous"]) == source.count(row["following"]) == 1, "unique adjacent owners")
    start, previous, following = (source.index(part) for part in (after, row["previous"], row["following"]))
    boundary = re.compile(r"\r?\n  }\r?\n").search(source, previous)
    lower = boundary.end() if boundary else -1
    _require(previous >= 0 and previous < lower <= start and start + len(after) <= following, "original owner slot")
    _require((start == 0 or source[start - 1] == "\n") and _OWNER.search(source[lower:start]) is None, "top-level helper placement")
    _require(before not in source, "not mixed BASE and current helpers")
    return source[:start] + before + source[start + len(after):]
