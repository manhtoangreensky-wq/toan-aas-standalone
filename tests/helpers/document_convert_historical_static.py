"""Finite test-only comparator chain; never used by current rendering or application."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTHORITIES = [
    ("document-convert-customer-copy-reviewed.json", "e162e15e4ddff0899dcf69bee7134576c7fac7a2fb35fb1857e555d1e70c6b63"),
    ("image-edit-customer-copy-reviewed.json", "7032192534419999f7528e3a6dbf08151b5db6ed96b3c49c7ecb300a6434007f"),
    ("pdf-utilities-customer-copy-reviewed.json", "fb1ffa41f9d924a11caf78b840d5ebc2a8e6a270eb49e91838868def71973870"),
]
FAIL = "Unreviewed document customer historical source"


def historical_customer_portal(source: str) -> str:
    assert isinstance(source, str), FAIL
    for filename, digest in AUTHORITIES:
        raw = (ROOT / "tests/fixtures" / filename).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest, FAIL + " authority"
        fixture = json.loads(raw)
        edits = [edit for edit in fixture["canonicalChanges"] if edit["file"] == "static/portal/portal.js"]
        assert edits and all(edit["count"] == 1 for edit in edits), FAIL + " edit count"
        phases = [(source.count(edit["old"]), source.count(edit["new"])) for edit in edits]
        if all(new == 0 for _, new in phases):
            continue
        assert all(new == 1 for _, new in phases), FAIL + " partial/duplicate/changed phase"
        for edit in reversed(edits):
            point = source.index(edit["new"])
            assert point >= 0, FAIL
            source = source[:point] + edit["old"] + source[point + len(edit["new"]):]
    return source
