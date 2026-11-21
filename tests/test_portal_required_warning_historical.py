"""Verify strict projection used only by older historical source checks."""
from pathlib import Path
import runpy
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = runpy.run_path(str(ROOT / "tests/helpers/portal_required_warning_historical.py"))
project = HELPER["required_warning_historical_source"]
BASE = "a09c7cc94a82537f77ab4e016d3dfa9ae7f23fcc"


@pytest.mark.parametrize("file", [HELPER["PORTAL"], HELPER["CATALOGUE"]])
def test_exact_projection_preserves_baseline_and_customer_bytes(file):
    original = subprocess.check_output(["git", "show", BASE + ":" + file], cwd=ROOT).decode("utf8").replace("\r\n", "\n")
    current = (ROOT / file).read_text(encoding="utf8").replace("\r\n", "\n")
    assert project(current, file) == original
    assert project(original, file) == original
    assert project("/* customer */\n" + current, file) == "/* customer */\n" + original
    assert project(current, "customer/unrelated.js") == current
    added = HELPER["NEW"] if file == HELPER["PORTAL"] else HELPER["ADDITIONS"]
    with pytest.raises(AssertionError, match=HELPER["FAIL"]):
        project(current + "\n" + added, file)
    changed = (current.replace(HELPER["NEW"], HELPER["NEW"].replace("uiText(", "uiTextUnknown("), 1)
               if file == HELPER["PORTAL"] else
               current.replace("Complete the required fields before continuing.", "UNREVIEWED", 1))
    with pytest.raises(AssertionError, match=HELPER["FAIL"]):
        project(changed, file)
