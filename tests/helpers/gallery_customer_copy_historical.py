"""Finite Gallery source inverse for old QA; never imported by application code."""
from pathlib import Path
import hashlib
import json
import re
from tests.helpers.gallery_readability_historical import gallery_readability_historical_source

ROOT = Path(__file__).resolve().parents[2]
RAW = (ROOT / "tests/fixtures/gallery-customer-copy.json").read_bytes().replace(b"\r\n", b"\n")
FAIL = "Unreviewed Gallery customer copy"
assert hashlib.sha256(RAW).hexdigest() == "c376690961cee3c23c17d0c4479f311b93e16bfcc8fda9d6abf6d6f07264e1ef", FAIL
FIXTURE = json.loads(RAW)
assert FIXTURE["base_sha"] == "bf95e4017717622d694cbef02fde07799a823a8a", FAIL
assert len(FIXTURE["records"]) == 56 and len(FIXTURE["copyRows"]) == 17, FAIL
FILES = {row["file"] for row in FIXTURE["applicationSources"]}


def gallery_customer_copy_historical_source(source: str, file: str) -> str:
    assert isinstance(source, str), FAIL
    source = gallery_readability_historical_source(source, file)
    if file not in FILES:
        return source
    records = [row for row in FIXTURE["records"] if row["file"] == file]
    if not any(row["new"] in source for row in records):
        return source
    previous = -1
    if file.endswith("portal-i18n.js"):
        declaration = r'^[ \t]*"(' + "|".join(re.escape(row["key"]) for row in FIXTURE["copyRows"]) + r')":'
        keys = re.findall(declaration, source, re.MULTILINE)
        assert all(keys.count(row["key"]) == 3 for row in FIXTURE["copyRows"]), FAIL
        for row in records:
            owner = "  const " + row["owner"] + " = {\n"
            lower = source.find(owner)
            upper = source.find("\n  };", lower)
            assert 0 <= lower < upper and source.count(owner) == 1, FAIL
            section = source[lower:upper + 6]
            marker = "    " + row["locale"] + ": {\n"
            lo = section.find(marker)
            index = ["vi", "en", "zh"].index(row["locale"])
            end = "\n    },\n    " + ["en", "zh"][index] + ": {" if index < 2 else "\n    }\n  };"
            hi = section.find(end, lo)
            assert 0 <= lo < hi and section.count(marker) == 1, FAIL
            at = source.find(row["new"])
            assert source.count(row["new"]) == 1, FAIL
            assert lower + lo + len(marker) <= at and at + len(row["new"]) <= lower + hi and at > previous, FAIL
            previous = at
    else:
        for row in records:
            owner = "  function " + row["owner"] + "("
            lower = source.find(owner)
            assert lower >= 0 and source.count(owner) == 1, FAIL
            at = source.find(row["new"])
            assert source.count(row["new"]) == 1, FAIL
            if row["owner"] == "freePromptGalleryCatalogState":
                helper = "  function freePromptGallerySourceText("
                start = source.find(helper)
                assert start >= 0 and source.count(helper) == 1 and at == start and at + len(row["new"]) == lower + len(row["old"]), FAIL
            else:
                end = source.find("\n  }\n", lower) + 5
                assert lower <= at and at + len(row["new"]) <= end, FAIL
            assert at > previous, FAIL
            previous = at
    for row in records:
        source = source.replace(row["new"], row["old"], 1)
    return source
