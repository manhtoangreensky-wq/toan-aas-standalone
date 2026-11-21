"""Pressure exact historical inputs; current151 forward acceptance is separate."""
from pathlib import Path
import re
import runpy
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = runpy.run_path(str(ROOT / "tests/helpers/media_fixed_feedback_historical_static.py"))
project, fail, groups = HELPER["historical_media_fixed_feedback_integration"], HELPER["FAIL"], HELPER["GROUPS"]
actual = (ROOT / "static/portal/integration.js").read_text(encoding="utf8").replace("\r\n", "\n")
baseline = subprocess.check_output(["git", "show", HELPER["FIXTURE"]["base"] + ":static/portal/integration.js"],
                                   cwd=ROOT).decode("utf8").replace("\r\n", "\n")


def test_newest_python_history_is_exact_idempotent_and_preserves_every_outside_byte():
    first, last = "/* CUSTOMER Facebook TikTok outside */\n", "\n/* CUSTOMER outside end */"
    assert project(actual) == baseline
    assert project(baseline) == baseline
    assert project(project(actual)) == baseline
    assert project(first + actual + last) == first + baseline + last
    assert project(first + last) == first + last


@pytest.mark.parametrize("index", range(8))
@pytest.mark.parametrize("kind", ["changed", "duplicate", "moved"])
def test_newest_python_history_rejects_changed_duplicate_or_moved_owned_regions(index, kind):
    group = groups[index]
    if kind == "changed":
        altered = re.sub(r"mediaWorkspace(?:FeedbackText|ErrorText)|audioWorkspace\.feedback", "UNREVIEWED_OWNED",
                         group["new"], count=1)
        assert altered != group["new"]
        malformed = actual.replace(group["new"], altered, 1)
    elif kind == "duplicate":
        malformed = actual + "\n" + group["new"]
    else:
        malformed = actual.replace(group["new"], "", 1) + "\n" + group["new"]
    with pytest.raises(AssertionError, match=fail):
        project(malformed)


def test_newest_python_history_rejects_wrong_types():
    for source in [None, 1, [], {}, b"source"]:
        with pytest.raises(AssertionError, match=fail):
            project(source)
