"""Pressure the FCH Python source leaf against independently frozen records."""
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from tests.helpers.feature_family_native_chrome_historical import feature_family_native_chrome_historical_source as project

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "tests/fixtures/feature-family-native-chrome.json").read_bytes().replace(b"\r\n", b"\n")
assert hashlib.sha256(RAW).hexdigest() == "6da6b40e9a7a62b11363b3af067306e721fb51ddbdb6042b70ac5d601fc7cbff"
FIXTURE = json.loads(RAW)
FILES = [pin["file"] for pin in FIXTURE["applicationSources"]]
BASE, CURRENT = {}, {}
for pin in FIXTURE["applicationSources"]:
    BASE[pin["file"]] = subprocess.check_output(["git", "show", FIXTURE["base_sha"] + ":" + pin["file"]], cwd=ROOT).decode().replace("\r\n", "\n")
    candidate = BASE[pin["file"]]
    for row in [row for row in FIXTURE["records"] if row["file"] == pin["file"]]:
        assert candidate.count(row["old"]) == 1
        candidate = candidate.replace(row["old"], row["new"], 1)
    assert hashlib.sha256(candidate.encode()).hexdigest() == pin["afterLfSha256"]
    CURRENT[pin["file"]] = candidate
FAIL = "Unreviewed feature-family native chrome"


@pytest.mark.parametrize("file", FILES)
def test_source_restores_exact_base_is_idempotent_and_keeps_unrelated_bytes(file):
    assert project(CURRENT[file], file) == BASE[file]
    assert project(project(CURRENT[file], file), file) == BASE[file]
    assert project(BASE[file], file) is BASE[file]
    assert project("/* CUSTOMER */\n" + CURRENT[file] + "\n/* TAIL */", file) == "/* CUSTOMER */\n" + BASE[file] + "\n/* TAIL */"
    assert project(CURRENT[file], "customer/unrelated.js") is CURRENT[file]


@pytest.mark.parametrize("file", FILES)
@pytest.mark.parametrize("kind", ["changed", "partial", "duplicate", "detached", "owner"])
def test_source_rejects_unreviewed_owned_region(file, kind):
    rows = [row for row in FIXTURE["records"] if row["file"] == file]
    row = rows[0]
    if kind == "changed":
        bad = CURRENT[file].replace(row["new"], row["new"].replace("featureCatalog." if file.endswith("portal-i18n.js") else "family.heading",
            "UNREVIEWED." if file.endswith("portal-i18n.js") else "family.UNREVIEWED", 1), 1)
    elif kind == "partial":
        bad = CURRENT[file].replace(row["new"], row["old"], 1)
    elif kind == "duplicate":
        bad = CURRENT[file] + "\n" + row["new"]
    elif kind == "detached":
        bad = CURRENT[file].replace(row["new"], "", 1) + "\n" + row["new"]
    else:
        marker = "  const FEATURE_CATALOG_MESSAGES = {" if file.endswith("portal-i18n.js") else "  function renderFeatureFamily(page, context) {"
        bad = CURRENT[file].replace(marker, marker + " UNREVIEWED", 1)
    if kind == "partial" and len(rows) == 1:
        assert project(bad, file) == BASE[file]
    else:
        with pytest.raises(AssertionError, match=FAIL):
            project(bad, file)


@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
def test_source_rejects_reordered_dictionary_records(locale):
    file = "static/portal/portal-i18n.js"
    rows = [row for row in FIXTURE["records"] if row["file"] == file and row.get("locale") == locale]
    bad = CURRENT[file].replace(rows[0]["new"], "__MOVE__", 1).replace(rows[1]["new"], rows[0]["new"], 1).replace("__MOVE__", rows[1]["new"], 1)
    with pytest.raises(AssertionError, match=FAIL):
        project(bad, file)


def test_marker_free_unrelated_source_is_not_normalized():
    assert project("CUSTOMER_TEXT", "static/portal/portal-i18n.js") == "CUSTOMER_TEXT"
