"""Historical FCH QA only, not application code."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
RAW = (ROOT / "tests/fixtures/feature-family-native-chrome.json").read_bytes().replace(b"\r\n", b"\n")
FAIL = "Unreviewed feature-family native chrome"
assert hashlib.sha256(RAW).hexdigest() == "6da6b40e9a7a62b11363b3af067306e721fb51ddbdb6042b70ac5d601fc7cbff", FAIL
FIXTURE = json.loads(RAW)
assert FIXTURE["base_sha"] == "363d6ca55081eea4089ebf489cd183b09ba1aa96", FAIL
assert len(FIXTURE["records"]) == 21 and FIXTURE["changedValues"] == 20, FAIL
FILES = {row["file"] for row in FIXTURE["applicationSources"]}
OWNED = {row["key"] for row in FIXTURE["copyRows"]}
assert len(OWNED) == 7, FAIL


def feature_family_native_chrome_historical_source(source: str, file: str) -> str:
    if file not in FILES:
        return source
    rows = [row for row in FIXTURE["records"] if row["file"] == file]
    if file.endswith("portal.js"):
        owner = "  function renderFeatureFamily(page, context) {\n"
        lower = source.find(owner)
        upper = source.find("\n  function ", lower + len(owner))
        body = source[lower:upper] if 0 <= lower < upper else ""
        if rows[0]["new"] not in source and '<div class="portal-section-heading"><div><h2>' not in body:
            return source
        assert 0 <= lower < upper and source.count(owner) == 1, FAIL
        assert source.count(rows[0]["new"]) == 1 and source.count(rows[0]["old"]) == 0, FAIL
        at = source.find(rows[0]["new"])
        assert lower <= at and at + len(rows[0]["new"]) <= upper, FAIL
    else:
        if not any(row["new"] in source for row in rows):
            return source
        declarations = re.findall(r'^[ \t]*"(' + "|".join(re.escape(key) for key in OWNED) + r')":', source, re.MULTILINE)
        counts = Counter(declarations)
        assert all(counts[key] == 3 for key in OWNED), FAIL
        owner, end = "  const FEATURE_CATALOG_MESSAGES = {\n", "\n  // Media Studio follows"
        lower, upper = source.find(owner), source.find(end, source.find(owner))
        assert 0 <= lower < upper and source.count(owner) == source.count(end) == 1, FAIL
        section, bounds, locales = source[lower:upper], {}, ("vi", "en", "zh")
        for index, locale in enumerate(locales):
            first = "    " + locale + ": {\n"
            last = "\n    },\n    " + locales[index + 1] + ": {" if index < 2 else "\n    }\n  };"
            a, b = section.find(first), section.find(last, section.find(first))
            assert 0 <= a < b and section.count(first) == section.count(last) == 1, FAIL
            bounds[locale] = (lower + a + len(first), lower + b)
        previous = -1
        for row in rows:
            at = source.find(row["new"])
            low, high = bounds[row["locale"]]
            assert low <= at and at + len(row["new"]) <= high and source.count(row["new"]) == 1 and at > previous, FAIL
            assert source.count(row["old"]) == 0, FAIL
            previous = at
    for row in rows:
        source = source.replace(row["new"], row["old"], 1)
    return source
