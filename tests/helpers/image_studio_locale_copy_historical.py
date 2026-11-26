"""Restore only the reviewed Image locale records for historical comparisons."""
import json
from pathlib import Path
from tests.helpers.image_composer_native_locale_historical import image_composer_native_locale_historical_source

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
VALIDATION = json.loads((ROOT / "tests/fixtures/image-studio-validation-contract.json").read_bytes())
assert VALIDATION["base"] == "5a95e48c9df922cc19a4bd83dfef46f2d85c04d2"
assert len(VALIDATION["records"]) == 30
FREE_TOOLS_COLORS = json.loads((ROOT / "tests/fixtures/free-tools-readable-colors-contract.json").read_bytes())
assert FREE_TOOLS_COLORS["base"] == "a8cf07490448548a2a1be6800fb7e146abeac726"
assert len(FREE_TOOLS_COLORS["records"]) == 9


def upstream_catalog_historical_source(source: str, file: str) -> str:
    records = [row for row in FREE_TOOLS_COLORS["catalog_sync"]["records"] if row["file"] == file]
    if not any(row["new"] in source for row in records):
        return source
    for record in reversed(records):
        assert source.count(record["new"]) == 1, "Unreviewed upstream catalog source"
        source = source.replace(record["new"], record["old"], 1)
    return source


def free_tools_readable_colors_historical_source(source: str, file: str) -> str:
    records = [row for row in FREE_TOOLS_COLORS["records"] if row["file"] == file]
    if not any(record["new"] in source for record in records):
        return source
    for record in reversed(records):
        assert source.count(record["new"]) == 1, "Unreviewed Free Tools color source"
        source = source.replace(record["new"], record["old"], 1)
    return source


def image_studio_validation_historical_source(source: str, file: str) -> str:
    source = image_composer_native_locale_historical_source(source, file)
    source = free_tools_readable_colors_historical_source(source, file)
    source = upstream_catalog_historical_source(source, file)
    if file == "static/portal/portal.js":
        records = FREE_TOOLS_COLORS["main_sync"]["portal_insertions"]
        if any(record in source for record in records):
            for record in records:
                assert source.count(record) == 1, "Unreviewed upstream realtime banner source"
                source = source.replace(record, "", 1)
    records = [row for row in VALIDATION["records"] if row["file"] == file]
    if not any(record["new"] in source for record in records):
        return source
    scopes = {
        '"Ý định Image Studio không hợp lệ."': "imageArtboardPayload",
        '"Loại biến thể Image Studio không hợp lệ."': "imageDirectionPayload",
    }
    for record in reversed(records):
        scope = scopes.get(record["old"])
        if scope:
            start = source.find("  function " + scope + "(")
            end = source.find("\n  }", start) + 4
            assert start >= 0 and end > start, "Missing Image validation scope"
            body = source[start:end]
            assert body.count(record["new"]) == 1, "Unreviewed scoped Image validation"
            source = source[:start] + body.replace(record["new"], record["old"], 1) + source[end:]
        else:
            assert source.count(record["new"]) == 1, "Unreviewed Image validation source"
            source = source.replace(record["new"], record["old"], 1)
    return source


def image_studio_locale_copy_historical_source(source: str, file: str) -> str:
    source = image_studio_validation_historical_source(source, file)
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
