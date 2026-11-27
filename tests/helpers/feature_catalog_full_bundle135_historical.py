"""Finite FBC135 projection for historical QA, never application code."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from tests.helpers.feature_family_native_chrome_historical import feature_family_native_chrome_historical_source
from tests.helpers.feature_family_readability_historical import feature_family_readability_historical_source
from tests.helpers.gallery_customer_copy_historical import gallery_customer_copy_historical_source

ROOT = Path(__file__).resolve().parents[2]
RAW = (ROOT / "tests/fixtures/feature-catalog-full-bundle135.json").read_bytes().replace(b"\r\n", b"\n")
FAIL = "Unreviewed full-bundle135 historical"
assert hashlib.sha256(RAW).hexdigest() == "bcde5343c0494c81f7deefeb9fcae35293f2ecee4e35e4a35ff4d84ae0f08d28", FAIL
FIXTURE = json.loads(RAW)
FILE = "static/portal/portal-i18n.js"
ROWS = FIXTURE["records"]
assert FIXTURE["base_sha"] == "fdfe2f753e641c5a5ecc7d6a19305fa3c42b7b30", FAIL
assert FIXTURE["beforeLfSha256"] == "a342ad1156e277bb3a529b6cda7b396fde528d19bae098a8662c392fb197ae1c", FAIL
assert FIXTURE["afterLfSha256"] == "6c6e866460c6e0473ecd7dbe6715673cf7ab6019b92f2dd44fa966f21c7105e2", FAIL
assert len(ROWS) == 289 and len(FIXTURE["changedExisting"]) == 286 and len(FIXTURE["missingKeys"]) == 39, FAIL
LOCALES = ("vi", "en", "zh")
ADDED = {f"featureCatalog.entry.{key}.{field}" for key in FIXTURE["missingKeys"] for field in ("title", "description")}
EXPECTED = {f"featureCatalog.entry.{key}.{field}" for key in FIXTURE["keys"] for field in ("title", "description")}
assert len(ADDED) == 78 and len(EXPECTED) == 270, FAIL


def feature_catalog_full_bundle135_historical_source(source: str, file: str) -> str:
    # Keep the original shared-owner failure classification before the new leaf.
    if file == FILE and any(key in ADDED for key in re.findall(
        r'^[ \t]*"(featureCatalog\.entry\.[a-z0-9_]+\.(?:title|description))":', source, re.MULTILINE
    )):
        assert source.count("  const FEATURE_CATALOG_MESSAGES = {") == 1, FAIL
        assert source.count("\n  // Media Studio follows") == 1, FAIL
    source = gallery_customer_copy_historical_source(source, file)
    source = feature_family_native_chrome_historical_source(source, file)
    source = feature_family_readability_historical_source(source, file)
    if file != FILE:
        return source
    declarations = re.findall(r'^[ \t]*"(featureCatalog\.entry\.[a-z0-9_]+\.(?:title|description))":', source, re.MULTILINE)
    # No new owned marker: preserve OLD/unknown edits for the original pin.
    if not any(key in ADDED for key in declarations):
        return source
    counts = Counter(declarations)
    assert all(counts[key] == 3 for key in EXPECTED), FAIL
    start, end = "  const FEATURE_CATALOG_MESSAGES = {", "\n  // Media Studio follows"
    lower, upper = source.find(start), source.find(end, source.find(start))
    assert 0 <= lower < upper and source.count(start) == source.count(end) == 1, FAIL
    section, bounds = source[lower:upper], {}
    for index, locale in enumerate(LOCALES):
        first = "    " + locale + ": {\n"
        last = "\n    },\n    " + LOCALES[index + 1] + ": {" if index < 2 else "\n    }\n  };"
        a, b = section.find(first), section.find(last, section.find(first))
        assert 0 <= a < b and section.count(first) == section.count(last) == 1, FAIL
        bounds[locale] = (lower + a + len(first), lower + b)
    previous = -1
    for row in ROWS:
        at = source.find(row["new"])
        low, high = bounds[row["locale"]]
        assert low <= at and at + len(row["new"]) <= high and source.count(row["new"]) == 1 and at > previous, FAIL
        previous = at
    for row in ROWS:
        source = source.replace(row["new"], row["old"], 1)
    return source
