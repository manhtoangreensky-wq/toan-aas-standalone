"""Restore only the reviewed Image locale records for historical comparisons."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "tests/fixtures/image-studio-locale-copy-contract.json").read_bytes())
assert CONTRACT["base"] == "d165bad407a51a8cf6339b019a073f8a1a1eb37a"
assert len(CONTRACT["records"]) == 32


def image_studio_locale_copy_historical_source(source: str, file: str) -> str:
    records = [row for row in CONTRACT["records"] if row["file"] == file]
    if not records or records[0]["new"] not in source:
        return source
    for record in reversed(records):
        assert source.count(record["new"]) == 1, "Unreviewed Image locale source"
        source = source.replace(record["new"], record["old"], 1)
    return source
