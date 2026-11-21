"""Pressure the exact newest historical projection; raw current acceptance is Node/151 pins."""
from pathlib import Path
import runpy
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = runpy.run_path(str(ROOT / "tests/helpers/media_detail_historical_static.py"))
inverse, fail, groups = HELPER["historical_media_detail_portal"], HELPER["FAIL"], HELPER["GROUPS"]
actual = (ROOT / "static/portal/portal.js").read_text(encoding="utf8").replace("\r\n", "\n")
baseline = subprocess.check_output(["git", "show", HELPER["FIXTURE"]["base"] + ":static/portal/portal.js"],
                                   cwd=ROOT).decode("utf8").replace("\r\n", "\n")


def test_detail_python_projection_is_exact_idempotent_and_preserves_unknown_outside_bytes():
    assert len(groups) == 7
    assert inverse(actual) == baseline
    assert inverse(baseline) == baseline
    assert inverse(inverse(actual)) == baseline
    first, last = '/* CUSTOMER Facebook TikTok <img>& */\n', '\n/* CUSTOMER suffix */'
    assert inverse(first + actual + last) == first + baseline + last
    assert inverse(first + last) == first + last


@pytest.mark.parametrize("index", range(7))
@pytest.mark.parametrize("kind", ["changed", "duplicate"])
def test_detail_python_projection_rejects_changed_or_duplicate_current_function(index, kind):
    group = groups[index]
    malformed = (actual.replace(group["new"], group["new"].replace("audioWorkspace", "UNKNOWN_WORKSPACE"), 1)
                 if kind == "changed" else actual + "\n" + group["new"])
    assert malformed != actual
    with pytest.raises(AssertionError, match=fail):
        inverse(malformed)


def test_detail_python_projection_rejects_wrong_types():
    for value in [None, 1, [], {}, b"source"]:
        with pytest.raises(AssertionError, match=fail):
            inverse(value)
