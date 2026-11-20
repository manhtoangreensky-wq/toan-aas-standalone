"""Exact historical leaf guards; physical current UI is tested separately."""
from pathlib import Path
import json
import runpy
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = runpy.run_path(str(ROOT / "tests/helpers/shared_select_historical_static.py"))
inverse, fail = HELPER["historical_shared_select_portal"], HELPER["FAIL"]
fixture = json.loads((ROOT / "tests/fixtures/shared-select-labels-reviewed.json").read_bytes())
edits = [row for row in fixture["canonicalChanges"] if row["file"] == "static/portal/portal.js"]
current = (ROOT / "static/portal/portal.js").read_text(encoding="utf8")
baseline = subprocess.check_output(["git", "show", fixture["base"] + ":static/portal/portal.js"], cwd=ROOT, text=True, encoding="utf8")


def test_shared_select_historical_leaf_is_exact_idempotent_and_preserves_customer_bytes():
    assert inverse(current) == baseline
    assert inverse(baseline) == baseline
    assert inverse(inverse(current)) == baseline
    prefix = '/* CUSTOMER Facebook TikTok media studio */\nconst customer = "sharedSelect.customer text";\n'
    suffix = "\n/* literal <img> & quotes */"
    assert inverse(prefix + current + suffix) == prefix + baseline + suffix
    assert inverse(prefix + suffix) == prefix + suffix


@pytest.mark.parametrize("index", range(3))
def test_shared_select_historical_leaf_rejects_partial_changed_duplicate_and_detached(index):
    edit = edits[index]
    for malformed in [
        current.replace(edit["new"], edit["old"], 1),
        current.replace(edit["new"], "", 1),
        current.replace(edit["new"], edit["new"].replace("uiText(", "uiTextUNKNOWN("), 1),
        current + "\n" + edit["new"],
        current.replace(edit["new"], "", 1) + "\n" + edit["new"],
    ]:
        with pytest.raises(AssertionError, match=fail):
            inverse(malformed)
    with pytest.raises(AssertionError, match=fail):
        inverse(edit["new"])


def test_shared_select_historical_leaf_keeps_strict_types_owners_and_owned_key_set():
    for value in [None, 42, [], {}]:
        with pytest.raises(AssertionError, match=fail):
            inverse(value)
    for malformed in [
        current.replace(HELPER["OWNER"], HELPER["OWNER"].replace("renderFields", "UNKNOWN")),
        current.replace(HELPER["NEXT"], HELPER["NEXT"].replace("statusMessage", "UNKNOWN")),
        current + '\nuiText("sharedSelect.unknown", "literal");',
        current + '\nsharedSelectUNKNOWN("literal");',
        current + '\nMESSAGES.vi["sharedSelect.unknown"] = "literal";',
    ]:
        with pytest.raises(AssertionError, match=fail):
            inverse(malformed)
