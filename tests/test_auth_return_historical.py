"""Pressure only the finite auth-return historical input inverse, never app code."""
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from tests.helpers.auth_return_historical import auth_return_historical_source as inverse

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "tests/fixtures/auth-return-history.json").read_bytes().decode().replace("\r\n", "\n")
FIXTURE = json.loads(RAW)
BASE = "fc9aef439d8fe7ecb00a2c68a167dad501f54eb9"
ROWS = FIXTURE["records"]
SOURCES = {
    row["file"]: (
        subprocess.check_output(["git", "show", f'{BASE}:{row["file"]}'], cwd=ROOT).decode().replace("\r\n", "\n"),
        (ROOT / row["file"]).read_bytes().decode().replace("\r\n", "\n"),
    ) for row in ROWS
}
FAIL = "Unreviewed auth return history"


def test_fixture_binds_only_two_complete_approved_pairs():
    assert hashlib.sha256(RAW.encode()).hexdigest() == "97a8aad3f4b8a0251a80222c7e5af4fe27b1b49e6d1cbfd2dd4f6d19797dfae3"
    assert FIXTURE["base_sha"] == BASE
    assert [row["file"] for row in ROWS] == ["static/portal/portal-auth.js", "static/portal/integration.js"]
    for row in ROWS:
        for name in ("before", "after"):
            assert hashlib.sha256(row[name].encode()).hexdigest() == row[name + "_sha256"]


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row["file"])
def test_independent_git_base_forward_construction_and_actual_raw_inverse(row):
    before, current = SOURCES[row["file"]]
    assert before.count(row["before"]) == 1
    assert current == before.replace(row["before"], row["after"], 1)
    assert inverse(current, row["file"]) == before
    assert inverse(before, row["file"]) is before
    assert inverse(inverse(current, row["file"]), row["file"]) == before


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row["file"])
@pytest.mark.parametrize("ending", ["\n", "\r\n"], ids=["LF", "CRLF"])
def test_outside_customer_bytes_and_encoding_are_never_normalized(row, ending):
    before, current = (value.replace("\n", ending) for value in SOURCES[row["file"]])
    prefix, suffix = "/* CUSTOMER 自由 α 25% */\r\n", "\r\n/* 客户 <b>& literal */"
    assert inverse(prefix + current + suffix, row["file"]) == prefix + before + suffix
    delta = "\r\n    /* UNKNOWN_INTERIOR 客户文本 25% */"
    assert inverse(current.replace(row["previous"], row["previous"] + delta, 1), row["file"]) == before.replace(row["previous"], row["previous"] + delta, 1)
    assert inverse(current, "foreign.js") is current
    assert inverse(prefix + suffix, row["file"]) == prefix + suffix


LINE_CASES = [(row, index) for row in ROWS for index, line in enumerate(row["after"].splitlines()) if line.strip()]


@pytest.mark.parametrize("row,index", LINE_CASES, ids=[row["file"] + "-line" + str(index) for row, index in LINE_CASES])
@pytest.mark.parametrize("ending", ["\n", "\r\n"], ids=["LF", "CRLF"])
def test_each_helper_line_is_frozen_and_altered_bytes_fail_closed(row, index, ending):
    current = SOURCES[row["file"]][1].replace("\n", ending)
    after = row["after"].replace("\n", ending)
    lines = after.split(ending)
    offset = len(lines[index]) - len(lines[index].lstrip())
    lines[index] = lines[index][:offset] + "X" + lines[index][offset + 1:]
    changed = ending.join(lines)
    assert changed != after
    with pytest.raises(ValueError, match=FAIL):
        inverse(current.replace(after, changed, 1), row["file"])


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row["file"])
@pytest.mark.parametrize("ending", ["\n", "\r\n"], ids=["LF", "CRLF"])
@pytest.mark.parametrize("kind", ["duplicate", "moved", "detached", "partial", "mixed", "previous", "following", "foreignOwner", "crossed", "inline"])
def test_malformed_helper_and_owner_slot_fail_closed(row, ending, kind):
    current = SOURCES[row["file"]][1].replace("\n", ending)
    after = row["after"].replace("\n", ending)
    malformed = {
        "duplicate": current + ending + after,
        "moved": after + current.replace(after, "", 1),
        "detached": after,
        "partial": current.replace(after, after[:len(after) // 2], 1),
        "mixed": current + row["before"].replace("\n", ending),
        "previous": current.replace(row["previous"], row["previous"].replace("randomKey", "unknownOwner"), 1),
        "following": current.replace(row["following"], "  function unknownOwner() {", 1),
        "foreignOwner": current.replace(after, "  function unknownOwner() {}" + ending + after, 1),
        "crossed": current.replace(after, "", 1) + after,
        "inline": current.replace(after, "/* displaced */" + after, 1),
    }[kind]
    with pytest.raises(ValueError, match=FAIL):
        inverse(malformed, row["file"])


def test_foreign_and_no_signal_input_identity_and_nonstring_guard():
    for file in ("foreign", "portal-auth.js", "static/portal/portal.js"):
        assert inverse(RAW, file) is RAW
    source = "/* old unrelated α\r\n */"
    for row in ROWS:
        assert inverse(source, row["file"]) is source
        with pytest.raises(ValueError, match=FAIL):
            inverse(None, row["file"])
