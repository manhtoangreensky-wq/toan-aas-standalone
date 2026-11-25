"""Keep the reviewed color inverse finite for Python historical readers."""
import json
import subprocess
from pathlib import Path

import pytest
from tests.helpers import image_studio_locale_copy_historical as historical
from tests.helpers.image_studio_locale_copy_historical import (
    free_tools_readable_colors_historical_source,
    image_studio_validation_historical_source,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "tests/fixtures/free-tools-readable-colors-contract.json").read_bytes())

@pytest.mark.parametrize("file", [
    "static/portal/portal.js", "static/portal/portal-theme.css", "static/portal/portal.css",
])
def test_catalog_projection_accepts_only_fixed_upstream_and_keeps_mutations(file):
    project = getattr(historical, "upstream_catalog_historical_source", None)
    assert callable(project)
    source = lambda revision: subprocess.check_output(
        ["git", "show", revision + ":" + file], cwd=ROOT, encoding="utf-8"
    ).replace("\r\n", "\n")
    before = source(CONTRACT["catalog_sync"]["prior"])
    upstream = source(CONTRACT["catalog_sync"]["base"])
    assert project(upstream, file) == before
    assert project(before, file) == before
    for prefix, suffix in (("", "\n/* unknown */"), ("/* customer */\n", ""), ("", " ")):
        assert project(prefix + upstream + suffix, file) == prefix + before + suffix
    record = next(row for row in CONTRACT["catalog_sync"]["records"] if row["file"] == file)
    assert before.count(record["old"]) == 1
    assert before.replace(record["old"], record["new"], 1) == upstream
    internal = lambda text: text.replace("\n", "\n/* unreviewed internal byte */\n", 1)
    assert project(internal(upstream), file) == internal(before)
    changed = upstream.replace(record["new"], record["new"].replace("\n", "\n/* mutation */\n", 1), 1)
    assert project(changed, file) == changed
    with pytest.raises(AssertionError, match="Unreviewed upstream catalog source"):
        project(upstream + record["new"], file)
    assert project(upstream, "unrelated.js") == upstream
    other = next(row["file"] for row in CONTRACT["catalog_sync"]["source_pins"] if row["file"] != file)
    assert project(upstream, other) == upstream
    physical = (ROOT / file).read_bytes().decode("utf-8").replace("\r\n", "\n")
    assert project(free_tools_readable_colors_historical_source(physical, file), file) == before


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
