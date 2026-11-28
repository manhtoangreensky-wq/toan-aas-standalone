"""Finite historical input inverse only; never used by application rendering."""
import hashlib
import json
from pathlib import Path

_raw = (Path(__file__).parents[1] / "fixtures" / "customer-language-cleanup-history.json").read_text(encoding="utf-8").replace("\r\n", "\n")
assert hashlib.sha256(_raw.encode()).hexdigest() == "7b7447e638ed9f9dbf250ec4b544f7dd786758009fceb2c4c7b2746befd3dacd"
_fixture = json.loads(_raw)
assert _fixture["base_sha"] == "2817dd9d221e04aa45945165ae60d5838cf9d920"
assert len(_fixture["records"]) == 48
assert len(_fixture["values"]) == 16
_files = {"static/portal/portal.js", "static/portal/portal-i18n.js"}
for _row in _fixture["records"]:
    assert _row["file"] in _files and _row["before"] and _row["after"]
    for _part in ("before", "after"):
        assert hashlib.sha256(_row[_part].encode()).hexdigest() == _row[f"{_part}_sha256"]


def customer_language_historical_source(source: str, file: str) -> str:
    """Peel only complete approved records; foreign content stays visible."""
    if file not in _files:
        return source
    ending = "\r\n" if "\r\n" in source else "\n"
    records = [
        {part: row[part].replace("\n", ending) for part in ("before", "after")}
        for row in _fixture["records"] if row["file"] == file
    ]
    if not any(row["after"] in source and (row["after"] not in row["before"] or row["before"] not in source) for row in records):
        return source
    for row in reversed(records):
        assert source.count(row["after"]) == 1, "Unreviewed customer language history"
        source = source.replace(row["after"], row["before"], 1)
    return source
