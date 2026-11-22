"""Exact input projection for historical tests predating option copy changes."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "tests/fixtures/image-studio-option-labels-contract.json").read_bytes())
FAIL = "Unreviewed Image Studio option copy"
assert CONTRACT["base"] == "f4c5b6a9821cf957ce107778fd9abd884075fd50", FAIL
assert len(CONTRACT["records"]) == 6, FAIL


def image_studio_options_historical_source(source: str, file: str) -> str:
    assert isinstance(source, str) and isinstance(file, str), FAIL
    records = [row for row in CONTRACT["records"] if row["file"] == file]
    marker = 'imageStudioText(`ratio.${value}`' if file.endswith("portal.js") else "IMAGE_STUDIO_RATIO_COPY_ROWS"
    if not records or marker not in source:
        return source
    for row in records:
        assert source.count(row["new"]) == 1, FAIL
    for row in reversed(records):
        source = source.replace(row["new"], row["old"], 1)
    return source
