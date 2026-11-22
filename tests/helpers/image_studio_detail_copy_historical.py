"""Exact inverse for source checks predating the reviewed detail-copy batch."""
from pathlib import Path
import json
import runpy

ROOT = Path(__file__).resolve().parents[2]
READ_PROJECT = runpy.run_path(str(ROOT / "tests/helpers/image_studio_read_feedback_historical.py"))["image_studio_read_feedback_historical_source"]
CONTRACT = json.loads((ROOT / "tests/fixtures/image-studio-detail-customer-copy-contract.json").read_bytes())
FAIL = "Unreviewed Image Studio detail copy"
assert CONTRACT["base"] == "f6aee803a72a80bf70cd0a4ce786858f94f9d7cc", FAIL
assert len(CONTRACT["records"]) == 22, FAIL


def image_studio_detail_copy_historical_source(source: str, file: str) -> str:
    source = READ_PROJECT(source, file)
    records = [row for row in CONTRACT["records"] if row["file"] == file]
    if not records or records[0]["new"] not in source:
        return source
    for row in records:
        assert source.count(row["new"]) == 1, FAIL
    for row in reversed(records):
        source = source.replace(row["new"], row["old"], 1)
    return source
