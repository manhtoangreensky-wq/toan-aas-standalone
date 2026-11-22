"""Exact source input projection for older historical comparisons only."""
from pathlib import Path
import json
import runpy

ROOT = Path(__file__).resolve().parents[2]
OPTIONS_PROJECT = runpy.run_path(str(ROOT / "tests/helpers/image_studio_options_historical.py"))["image_studio_options_historical_source"]
CONTRACT = json.loads((ROOT / "tests/fixtures/image-studio-create-fields-contract.json").read_bytes())
FAIL = "Unreviewed Image Studio field copy"
assert CONTRACT["base"] == "05b7ba761bd35cf4da498443db9046ed59429d90", FAIL
assert len(CONTRACT["records"]) == 2 and len(CONTRACT["rows"]) == 18, FAIL


def image_studio_fields_historical_source(source: str, file: str) -> str:
    assert isinstance(source, str) and isinstance(file, str), FAIL
    source = OPTIONS_PROJECT(source, file)
    record = next((row for row in CONTRACT["records"] if row["file"] == file), None)
    marker = 'imageStudioText("form.' if file.endswith("portal.js") else "IMAGE_STUDIO_FORM_COPY_ROWS"
    if record is None or marker not in source:
        return source
    assert source.count(record["new"]) == 1, FAIL
    at = source.index(record["new"])
    start = source.find("  function imageStudioArtboardFields(context) {" if file.endswith("portal.js") else "  const IMAGE_STUDIO_COPY_ROWS = [")
    end = source.find("  function imageStudioArtboardValues(value) {" if file.endswith("portal.js") else "  const IMAGE_STUDIO_LIBRARY_COPY_ROWS = [")
    assert 0 <= start <= at < end, FAIL
    return source.replace(record["new"], record["old"], 1)
