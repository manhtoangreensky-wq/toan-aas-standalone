"""Exact finite source inverse for historical checks, not current UI."""
import hashlib
import json
from pathlib import Path
from tests.helpers.customer_language_cleanup_historical import customer_language_historical_source

_raw = (Path(__file__).parents[1] / "fixtures" / "customer-natural-followup-history.json").read_text(encoding="utf-8").replace("\r\n", "\n")
assert hashlib.sha256(_raw.encode()).hexdigest() == "d74a68658d1dedb5dc986debc874f45dfe50355175414e64f1d4fff68bb68eb6"
_fixture = json.loads(_raw)
assert _fixture["base_sha"] == "469f70063217814522b674272185227d93c8a08c"
assert len(_fixture["records"]) == 2
assert len(_fixture["values"]) == 413


def customer_natural_historical_source(source: str, file: str) -> str:
    """Remove only a complete approved wording record, retaining foreign bytes."""
    source = customer_language_historical_source(source, file)
    row = next((item for item in _fixture["records"] if item["file"] == file), None)
    if row is None:
        return source
    for part in ("before", "after"):
        assert hashlib.sha256(row[part].encode()).hexdigest() == row[f"{part}_sha256"]
    if file.endswith("portal.js"):
        if row["owner"] not in source and row["after"] not in source:
            return source
        if source.count(row["before"]) == 1 and row["after"] not in source:
            return source
    elif (
        "Natural customer wording; behavior and data remain unchanged." not in source
        and '"summary.companion": "Ứng dụng liên kết"' not in source
    ):
        return source
    assert source.count(row["after"]) == 1, "Unreviewed customer natural-copy history"
    return source.replace(row["after"], row["before"], 1)
