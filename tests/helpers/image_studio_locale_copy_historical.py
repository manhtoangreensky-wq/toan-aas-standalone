"""Restore only the reviewed Image locale records for historical comparisons."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "tests/fixtures/image-studio-locale-copy-contract.json").read_bytes())
assert CONTRACT["base"] == "d165bad407a51a8cf6339b019a073f8a1a1eb37a"
assert len(CONTRACT["records"]) == 32
ROOT_METADATA = json.loads((ROOT / "tests/fixtures/image-studio-root-metadata-contract.json").read_bytes())
assert ROOT_METADATA["base"] == "3d21e950fb8e676ffd0b8c945a5ff6d9c8425736"
assert len(ROOT_METADATA["records"]) == 7
ROOT_HEADING = json.loads((ROOT / "tests/fixtures/image-studio-root-heading-contract.json").read_bytes())
assert ROOT_HEADING["base"] == "3d21e950fb8e676ffd0b8c945a5ff6d9c8425736"
assert len(ROOT_HEADING["records"]) == 1


def image_studio_locale_copy_historical_source(source: str, file: str) -> str:
    heading_record = ROOT_HEADING["records"][0]
    if file == heading_record["file"] and heading_record["new"] in source:
        assert source.count(heading_record["new"]) == 1, "Unreviewed Image root heading CSS"
        source = source.replace(heading_record["new"], heading_record["old"], 1)
    root_records = [row for row in ROOT_METADATA["records"] if row["file"] == file]
    if root_records and root_records[0]["new"] in source:
        for record in reversed(root_records):
            assert source.count(record["new"]) == 1, "Unreviewed Image root metadata source"
            source = source.replace(record["new"], record["old"], 1)
    records = [row for row in CONTRACT["records"] if row["file"] == file]
    if not records or records[0]["new"] not in source:
        return source
    for record in reversed(records):
        assert source.count(record["new"]) == 1, "Unreviewed Image locale source"
        source = source.replace(record["new"], record["old"], 1)
    return source
