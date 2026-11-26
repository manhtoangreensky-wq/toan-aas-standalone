"""Pressure the Python FBC leaf without weakening any older source assertion."""
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from tests.helpers.feature_catalog_full_bundle135_historical import (
    feature_catalog_full_bundle135_historical_source as project,
)

ROOT = Path(__file__).resolve().parents[1]
RAW = (ROOT / "tests/fixtures/feature-catalog-full-bundle135.json").read_bytes().replace(b"\r\n", b"\n")
assert hashlib.sha256(RAW).hexdigest() == "bcde5343c0494c81f7deefeb9fcae35293f2ecee4e35e4a35ff4d84ae0f08d28"
FIXTURE = json.loads(RAW)
FILE = FIXTURE["applicationFile"]
CURRENT = (ROOT / FILE).read_text(encoding="utf8").replace("\r\n", "\n")
BASE = subprocess.check_output(["git", "show", FIXTURE["base_sha"] + ":" + FILE], cwd=ROOT).decode("utf8").replace("\r\n", "\n")
FAIL = "Unreviewed full-bundle135 historical"


def test_python_leaf_restores_exact_frozen_base_and_is_idempotent():
    assert project(CURRENT, FILE) == BASE
    assert project(project(CURRENT, FILE), FILE) == BASE
    assert project(BASE, FILE) is BASE


@pytest.mark.parametrize("prefix,suffix", [("/* customer outside */\n", ""), ("", "\n/* customer tail */")])
def test_python_leaf_preserves_unknown_outside_bytes(prefix, suffix):
    assert project(prefix + CURRENT + suffix, FILE) == prefix + BASE + suffix


def test_python_leaf_preserves_unknown_entry_and_non_i18n_input():
    marker = '      "featureCatalog.entry.owner_future.title": "CUSTOMER",\n'
    # Insert outside the frozen addition block (whose trailing anchor is dashboard.title).
    anchor = '      "featureCatalog.entry.projects.title":'
    assert not any(anchor in row["new"] for row in FIXTURE["records"])
    current = CURRENT.replace(anchor, marker + anchor, 1)
    expected = BASE.replace(anchor, marker + anchor, 1)
    assert project(current, FILE) == expected
    assert project(CURRENT, "customer/unrelated.js") is CURRENT
    old_unknown = BASE.replace(anchor, marker + anchor, 1)
    assert project(old_unknown, FILE) is old_unknown


@pytest.mark.parametrize("locale", ["vi", "en", "zh"])
@pytest.mark.parametrize("kind", ["changed", "partial", "duplicate", "detached", "reordered"])
def test_python_leaf_rejects_malformed_owned_records(locale, kind):
    records = [row for row in FIXTURE["records"] if row["locale"] == locale]
    row, other = records[0], records[1]
    if kind == "changed":
        bad = CURRENT.replace(row["new"], row["new"].replace('"featureCatalog.', '"UNREVIEWED.', 1), 1)
    elif kind == "partial":
        bad = CURRENT.replace(row["new"], row["old"], 1)
    elif kind == "duplicate":
        bad = CURRENT + "\n" + row["new"]
    elif kind == "detached":
        bad = CURRENT.replace(records[-1]["new"], "", 1) + "\n" + records[-1]["new"]
    else:
        bad = CURRENT.replace(row["new"], "__MOVE__", 1).replace(other["new"], row["new"], 1).replace("__MOVE__", other["new"], 1)
    with pytest.raises(AssertionError, match=FAIL):
        project(bad, FILE)


@pytest.mark.parametrize("marker", ['  const FEATURE_CATALOG_MESSAGES = {', '\n  // Media Studio follows'])
def test_python_leaf_rejects_detached_owner_or_duplicated_owner_boundary(marker):
    with pytest.raises(AssertionError, match=FAIL):
        project(CURRENT + "\n" + marker, FILE)


def test_python_leaf_marker_free_unknown_edits_remain_visible_to_original_pin():
    old_changed = BASE.replace("featureCatalog.entry.dashboard.description", "CUSTOMER_UNKNOWN", 1)
    assert project(old_changed, FILE) is old_changed
