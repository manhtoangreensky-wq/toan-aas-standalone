"""Keep the reviewed color inverse finite for Python historical readers."""
import json
import subprocess
from pathlib import Path

import pytest
from tests.helpers.image_studio_locale_copy_historical import (
    free_tools_readable_colors_historical_source,
    image_studio_validation_historical_source,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "tests/fixtures/free-tools-readable-colors-contract.json").read_bytes())


@pytest.mark.parametrize("file", ["static/portal/portal.js", "static/portal/portal-theme.css"])
def test_color_inverse_keeps_unknown_changes_and_rejects_partial_or_duplicated_records(file):
    base = subprocess.check_output(
        ["git", "show", CONTRACT["base"] + ":" + file], cwd=ROOT, encoding="utf-8"
    ).replace("\r\n", "\n")
    records = [row for row in CONTRACT["records"] if row["file"] == file]
    candidate = base
    for record in records:
        assert candidate.count(record["old"]) == 1
        candidate = candidate.replace(record["old"], record["new"], 1)
    assert free_tools_readable_colors_historical_source(candidate, file) == base
    assert free_tools_readable_colors_historical_source(base, file) == base
    assert free_tools_readable_colors_historical_source(candidate + "\n/* unknown */", file) == base + "\n/* unknown */"
    assert free_tools_readable_colors_historical_source(candidate, "unrelated.css") == candidate
    with pytest.raises(AssertionError):
        free_tools_readable_colors_historical_source(candidate + records[0]["new"], file)
    with pytest.raises(AssertionError):
        free_tools_readable_colors_historical_source(
            candidate.replace(records[-1]["new"], records[-1]["old"], 1), file
        )


def test_upstream_banner_inverse_is_finite_and_keeps_unrelated_bytes():
    file = "static/portal/portal.js"
    source = lambda revision: subprocess.check_output(
        ["git", "show", revision + ":" + file], cwd=ROOT, encoding="utf-8"
    ).replace("\r\n", "\n")
    before = source(CONTRACT["base"])
    upstream = source(CONTRACT["main_sync"]["base"])
    inverse = lambda text: image_studio_validation_historical_source(text, file)
    assert inverse(upstream) == before
    assert inverse(before) == before
    assert inverse(upstream + "\n/* unknown */") == before + "\n/* unknown */"
    for record in CONTRACT["main_sync"]["portal_insertions"]:
        with pytest.raises(AssertionError):
            inverse(upstream + record)
        with pytest.raises(AssertionError):
            inverse(upstream.replace(record, "", 1))
