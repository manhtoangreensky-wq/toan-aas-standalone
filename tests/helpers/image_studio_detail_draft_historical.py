"""Finite inverse for the reviewed same-revision Image form preservation."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "tests/fixtures/image-studio-detail-draft-contract.json").read_bytes())
assert CONTRACT["base"] == "e177ce5f5791fd22e517d95706331051223e0ccb"
assert len(CONTRACT["records"]) == 1


def image_studio_detail_draft_historical_source(source: str, file: str) -> str:
    record = CONTRACT["records"][0]
    if record["file"] != file or record["new"] not in source:
        return source
    assert source.count(record["new"]) == 1, "Unreviewed Image detail form preservation"
    return source.replace(record["new"], record["old"], 1)
