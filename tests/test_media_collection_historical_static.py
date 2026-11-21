"""Exact Python historical leaf guards; current physical UI acceptance is separate."""
from pathlib import Path
import hashlib
import json
import runpy
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = runpy.run_path(str(ROOT / "tests/helpers/media_collection_historical_static.py"))
inverse, fail = HELPER["historical_media_collection_portal"], HELPER["FAIL"]
detail_inverse = runpy.run_path(str(ROOT / "tests/helpers/media_detail_historical_static.py"))["historical_media_detail_portal"]
raw = (ROOT / "tests/fixtures/media-collection-locale-reviewed.json").read_bytes()
fixture = json.loads(raw)
groups = [row for row in fixture["historicalFragments"] if row["file"] == "static/portal/portal.js"]
actual = detail_inverse((ROOT / "static/portal/portal.js").read_text(encoding="utf8").replace("\r\n", "\n"))
baseline = subprocess.check_output(["git", "show", fixture["base"] + ":static/portal/portal.js"],
                                   cwd=ROOT).decode("utf8").replace("\r\n", "\n")


def test_media_python_leaf_restores_only_exact_reviewed_regions_and_preserves_outside_bytes():
    assert hashlib.sha256(raw).hexdigest() == "f0da75ecb63d7f0abc432053441502cd8db99fcc487aa4b192a6514c84ea0515"
    assert len(groups) == 5
    assert inverse(actual) == baseline
    assert inverse(baseline) == baseline
    assert inverse(inverse(actual)) == baseline
    prefix, suffix = "/* CUSTOMER Facebook TikTok media studio <img>& */\n", '\nconst customer="literal";'
    assert inverse(prefix + actual + suffix) == prefix + baseline + suffix
    assert inverse(prefix + suffix) == prefix + suffix


@pytest.mark.parametrize("index", range(5))
@pytest.mark.parametrize("kind", ["changed", "duplicate", "detached", "owner", "boundary"])
def test_media_python_leaf_rejects_changed_duplicate_detached_or_wrong_owner(index, kind):
    group = groups[index]
    if kind == "changed":
        malformed = actual.replace(group["new"], group["new"].replace("audioWorkspace", "UNKNOWN_WORKSPACE"), 1)
    elif kind == "duplicate":
        malformed = actual + "\n" + group["new"]
    elif kind == "detached":
        malformed = actual.replace(group["new"], "", 1) + "\n" + group["new"]
    elif kind == "owner":
        malformed = actual.replace(group["owner"], group["owner"].replace("function ", "function UNKNOWN_"), 1)
    else:
        malformed = actual.replace(group["next"], group["next"].replace("function ", "function UNKNOWN_"), 1)
    with pytest.raises(AssertionError, match=fail):
        inverse(malformed)


def test_media_python_leaf_retains_strict_input_types():
    for value in [None, 1, [], {}, b"source"]:
        with pytest.raises(AssertionError, match=fail):
            inverse(value)
