"""Historical comparator behavior, independent of current UI renderer acceptance."""
from pathlib import Path
import json
import runpy
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
inverse = runpy.run_path(str(ROOT / "tests/helpers/document_convert_historical_static.py"))["historical_customer_portal"]
fixture = json.loads((ROOT / "tests/fixtures/document-convert-customer-copy-reviewed.json").read_bytes())
edits = [row for row in fixture["canonicalChanges"] if row["file"] == "static/portal/portal.js"]
actual = (ROOT / "static/portal/portal.js").read_text(encoding="utf8")
baseline = subprocess.check_output(["git", "show", fixture["base"] + ":static/portal/portal.js"], cwd=ROOT, text=True, encoding="utf8")


def test_current_and_prior_phases_restore_same_exact_historical_portal_without_touching_outside_bytes():
    assert len(edits) == 8
    assert inverse(actual) == inverse(baseline)
    assert inverse(inverse(actual)) == inverse(actual)
    prefix = "/* CUSTOMER media studio Facebook docConvertImagesUiTitle */\n"
    suffix = '\nconst customer = "provider <b>literal</b>";\n'
    assert inverse(prefix + actual + suffix) == prefix + inverse(baseline) + suffix
    assert inverse(prefix + suffix) == prefix + suffix


@pytest.mark.parametrize("index", range(8))
def test_partial_changed_or_duplicate_owned_fragment_is_rejected(index):
    edit = edits[index]
    for malformed in [
        actual.replace(edit["new"], edit["old"], 1),
        actual.replace(edit["new"], "", 1),
        actual + "\n" + edit["new"],
    ]:
        with pytest.raises(AssertionError, match="Unreviewed document customer historical source"):
            inverse(malformed)


def test_invalid_type_is_not_silently_coerced():
    for value in [None, 42, [], {}]:
        with pytest.raises(AssertionError, match="Unreviewed document customer historical source"):
            inverse(value)
