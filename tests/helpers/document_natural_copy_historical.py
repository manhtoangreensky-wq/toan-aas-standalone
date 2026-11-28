"""Finite old-source reader for historical assertions; never current UI."""
import hashlib
import json
from pathlib import Path
from tests.helpers.customer_natural_followup_historical import customer_natural_historical_source

_raw = (Path(__file__).parents[1] / "fixtures" / "document-natural-copy-history.json").read_text(encoding="utf-8").replace("\r\n", "\n")
assert hashlib.sha256(_raw.encode()).hexdigest() == "743eea1bfe1b7ae9a192f57f9a153d93007d9097c830b9fd110ec53d8a258098"
_fixture = json.loads(_raw)
assert _fixture["base_sha"] == "cf94b23e6a26010e88ebcd33b36623204c784c9a"
assert len(_fixture["records"]) == 60


def document_natural_historical_source(source: str, file: str) -> str:
    """Undo only the exact approved copy records; preserve all unknown bytes."""
    source = customer_natural_historical_source(source, file)
    allowed = {"static/portal/portal.js", "static/portal/integration.js", "static/portal/portal-i18n.js"}
    if file not in allowed or "docPlain" not in source:
        return source
    for row in reversed(_fixture["records"]):
        if row["file"] != file:
            continue
        assert hashlib.sha256(row["before"].encode()).hexdigest() == row["before_sha256"]
        assert hashlib.sha256(row["after"].encode()).hexdigest() == row["after_sha256"]
        assert source.count(row["after"]) == 1, "Unreviewed document natural-copy history"
        source = source.replace(row["after"], row["before"], 1)
    assert "docPlain" not in source, "Unknown or partial document copy"
    return source
