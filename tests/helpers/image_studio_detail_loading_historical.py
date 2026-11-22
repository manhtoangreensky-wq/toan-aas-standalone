"""Restore only the reviewed Image detail loading records for historical assertions."""
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRAFT_PROJECT = runpy.run_path(str(ROOT / "tests/helpers/image_studio_detail_draft_historical.py"))["image_studio_detail_draft_historical_source"]
CONTRACT = json.loads((ROOT / "tests/fixtures/image-studio-detail-loading-contract.json").read_bytes())
assert CONTRACT["base"] == "e177ce5f5791fd22e517d95706331051223e0ccb"
assert len(CONTRACT["records"]) == 3


def image_studio_detail_loading_historical_source(source: str, file: str) -> str:
    source = DRAFT_PROJECT(source, file)
    record = next((row for row in CONTRACT["records"] if row["file"] == file), None)
    if not record or record["new"] not in source:
        return source
    assert source.count(record["new"]) == 1, "Unreviewed Image Studio detail loading"
    assert record["old"] not in source.replace(record["new"], "", 1), "Mixed Image Studio detail loading"
    return source.replace(record["new"], record["old"], 1)
