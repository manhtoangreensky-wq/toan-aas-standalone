"""Finite inverse for older source assertions; never used by application code."""
import json
from pathlib import Path
from tests.helpers.native_label_recovery_historical import native_label_recovery_historical_source

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "tests/fixtures/image-composer-native-locale-contract.json").read_bytes())
assert CONTRACT["base"] == "6ec003dbf8f80739f5fb93ff7bd1d7cc703c6792"
assert len(CONTRACT["records"]) == 39
CHANGES = [*CONTRACT["records"], *CONTRACT.get("amendments", [])]


def image_composer_native_locale_historical_source(source: str, file: str) -> str:
    source = native_label_recovery_historical_source(source, file)
    records = [row for row in CHANGES if row["file"] == file]
    if not any(row["new"] in source for row in records):
        return source
    for row in reversed(records):
        assert source.count(row["new"]) == 1, "Unreviewed Composer locale source"
        source = source.replace(row["new"], row["old"], 1)
    return source
