"""Finite inverse for reviewed native-label records; never application code."""
import json
from pathlib import Path
from tests.helpers.feature_catalog_full_bundle135_historical import feature_catalog_full_bundle135_historical_source

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "tests/fixtures/native-label-recovery-contract.json").read_bytes())
assert CONTRACT["base"] == "1a57e62152855b1cff39956d43ad0ccfd5f3d5cb"
assert len(CONTRACT["records"]) == 8
CHANGES = [*CONTRACT["records"], *CONTRACT.get("amendments", [])]


def native_label_recovery_historical_source(source: str, file: str) -> str:
    source = feature_catalog_full_bundle135_historical_source(source, file)
    records = [row for row in CHANGES if row["file"] == file]
    if not any(row["new"] in source for row in records):
        return source
    for row in reversed(records):
        assert source.count(row["new"]) == 1, "Unreviewed native label recovery source"
        source = source.replace(row["new"], row["old"], 1)
    return source
