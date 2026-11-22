"""Exact inverse for historical source assertions before read-feedback changes."""
from pathlib import Path
import json
import runpy

ROOT = Path(__file__).resolve().parents[2]
LOADING_PROJECT = runpy.run_path(str(ROOT / "tests/helpers/image_studio_detail_loading_historical.py"))["image_studio_detail_loading_historical_source"]
CONTRACT = json.loads((ROOT / "tests/fixtures/image-studio-read-feedback-contract.json").read_bytes())
FAIL = "Unreviewed Image Studio read feedback"
assert CONTRACT["base"] == "ef3643d84c269aa2a07e411debe400a44f72d8e6", FAIL
assert len(CONTRACT["records"]) == 6, FAIL


def image_studio_read_feedback_historical_source(source: str, file: str) -> str:
    source = LOADING_PROJECT(source, file)
    records = [row for row in CONTRACT["records"] if row["file"] == file]
    if not records or records[0]["new"] not in source:
        return source
    for row in records:
        assert source.count(row["new"]) == 1, FAIL
    for row in reversed(records):
        source = source.replace(row["new"], row["old"], 1)
    return source
