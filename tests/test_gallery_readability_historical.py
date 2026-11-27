"""Pressure-test the finite Python inverse using public BASE + frozen GPC56."""
from pathlib import Path
import hashlib
import json
import subprocess
import pytest
from tests.helpers.gallery_readability_historical import gallery_readability_historical_source as project
from tests.helpers.feature_family_readability_historical import ADDITION as FAMILY_ADDITION

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/gallery-readability.json").read_bytes())
PRIOR = json.loads((ROOT / "tests/fixtures/gallery-customer-copy.json").read_bytes())
CSS_FILE = "static/portal/portal-theme.css"
RECORD = FIXTURE["portalRecord"]
PORTAL_FILE = RECORD["file"]
FILES = [CSS_FILE, PORTAL_FILE]
ADDITION = "\n" + FIXTURE["cssMarker"] + "\n" + "\n".join(FIXTURE["cssRules"]) + "\n"
BASE, BEFORE, CURRENT = {}, {}, {}
for file in FILES:
    BASE[file] = subprocess.check_output(
        ["git", "show", FIXTURE["base_sha"] + ":" + file], cwd=ROOT
    ).decode().replace("\r\n", "\n")
    source = BASE[file]
    for row in [row for row in PRIOR["records"] if row["file"] == file]:
        assert source.count(row["old"]) == 1
        source = source.replace(row["old"], row["new"], 1)
    BEFORE[file] = source
    CURRENT[file] = source + ADDITION if file == CSS_FILE else source.replace(RECORD["old"], RECORD["new"], 1)


def test_pre_gpr_source_matches_independently_frozen_public_base_and_gpc56_pins():
    assert hashlib.sha256(BEFORE[CSS_FILE].encode()).hexdigest() == FIXTURE["cssBeforeLfSha256"]
    assert hashlib.sha256(BEFORE[PORTAL_FILE].encode()).hexdigest() == FIXTURE["portalBeforeLfSha256"]
    assert BEFORE[CSS_FILE].endswith(FAMILY_ADDITION)
    assert BEFORE[PORTAL_FILE].count(RECORD["old"]) == 1


def test_unrelated_old_css_font_edit_survives_without_a_full_source_hash_gate():
    bad = CURRENT[CSS_FILE].replace("font-size: 16px;", "font-size: 17px;", 1)
    expected = BEFORE[CSS_FILE].replace("font-size: 16px;", "font-size: 17px;", 1)
    assert expected != BEFORE[CSS_FILE]
    assert project(bad, CSS_FILE) == expected


def test_unknown_bytes_inside_function_but_outside_metric_slot_survive():
    point = "    const catalogTotal ="
    start = CURRENT[PORTAL_FILE].index("  function renderFreePromptGallery(")
    at = CURRENT[PORTAL_FILE].index(point, start)
    edited = CURRENT[PORTAL_FILE][:at] + "    /* UNKNOWN */\n" + CURRENT[PORTAL_FILE][at:]
    before_at = BEFORE[PORTAL_FILE].index(point, BEFORE[PORTAL_FILE].index("  function renderFreePromptGallery("))
    assert project(edited, PORTAL_FILE) == (
        BEFORE[PORTAL_FILE][:before_at] + "    /* UNKNOWN */\n" + BEFORE[PORTAL_FILE][before_at:]
    )


@pytest.mark.parametrize("file", FILES)
def test_public_base_and_pre_gpr_are_noops(file):
    assert project(BASE[file], file) is BASE[file]
    assert project(BEFORE[file], file) is BEFORE[file]


@pytest.mark.parametrize("file", FILES)
def test_exact_gpr_inverse_restores_pre_gpr_and_is_idempotent(file):
    assert project(CURRENT[file], file) == BEFORE[file]
    assert project(project(CURRENT[file], file), file) == BEFORE[file]


@pytest.mark.parametrize("file", FILES)
def test_unknown_prefix_suffix_and_internal_bytes_survive(file):
    assert project("/* CUSTOMER */\r\n" + CURRENT[file] + "\r\n/* TAIL */", file) == (
        "/* CUSTOMER */\r\n" + BEFORE[file] + "\r\n/* TAIL */"
    )
    assert project(CURRENT[file].replace("\n", "\n/* UNKNOWN */\n", 1), file) == (
        BEFORE[file].replace("\n", "\n/* UNKNOWN */\n", 1)
    )


@pytest.mark.parametrize("file", FILES)
def test_unrelated_target_is_unchanged_even_with_malformed_owned_input(file):
    bad = CURRENT[file] + ADDITION + RECORD["new"]
    assert project(bad, "customer/unrelated.js") is bad


CSS = CURRENT[CSS_FILE]
RULES = FIXTURE["cssRules"]
CSS_CASES = {
    "partial rule set": CSS.replace(RULES[5] + "\n", "", 1),
    "changed CSS value": CSS.replace(RULES[0], RULES[0].replace("font-size: 16px;", "font-size: 17px;", 1), 1),
    "missing marker": CSS.replace(FIXTURE["cssMarker"], "", 1),
    "duplicate marker": CSS + FIXTURE["cssMarker"],
    "duplicate addition": CSS + ADDITION,
    "detached addition": ADDITION + BEFORE[CSS_FILE],
    "addition before prior FCR": BEFORE[CSS_FILE].replace(FAMILY_ADDITION, ADDITION + FAMILY_ADDITION, 1),
    "gap after prior FCR": BEFORE[CSS_FILE] + "\n/* UNKNOWN GAP */\n" + ADDITION,
    "reordered rules": CSS.replace(RULES[0] + "\n" + RULES[1], RULES[1] + "\n" + RULES[0], 1),
    "duplicate selector owner": CSS + RULES[0].replace("16px", "18px", 1) + "\n",
    "selector without marker": BEFORE[CSS_FILE] + "\n" + RULES[0] + "\n",
    "changed prior FCR anchor": CSS.replace(
        FAMILY_ADDITION, FAMILY_ADDITION.replace("color: var(--portal-text);", "color: red;", 1), 1
    ),
}


@pytest.mark.parametrize("name", CSS_CASES)
def test_css_inverse_rejects_unreviewed_owned_addition(name):
    bad = CSS_CASES[name]
    assert bad != CSS
    with pytest.raises(AssertionError, match="Unreviewed Gallery readability"):
        project(bad, CSS_FILE)


PORTAL = CURRENT[PORTAL_FILE]
OWNER = "  function renderFreePromptGallery("
INTRO = '<section class="portal-content-prompt-pack-intro">'
PORTAL_CASES = {
    "changed condition": PORTAL.replace(RECORD["new"], RECORD["new"].replace("canBrowse", "canRead"), 1),
    "changed false branch": PORTAL.replace(RECORD["new"], RECORD["new"].replace('` : ""}', '` : "pending"}'), 1),
    "changed metric content": PORTAL.replace(
        RECORD["new"], RECORD["new"].replace("intro.stat.categories", "intro.stat.UNKNOWN"), 1
    ),
    "changed metrics opening tag": PORTAL.replace(RECORD["new"], RECORD["new"].replace("<dl>", "<ul>"), 1),
    "partial conditional opening": PORTAL.replace(RECORD["new"], RECORD["new"][len("${canBrowse ? `"):], 1),
    "partial conditional closing": PORTAL.replace(RECORD["new"], RECORD["new"][:-len('` : ""}')], 1),
    "duplicate fragment": PORTAL + "\n" + RECORD["new"],
    "detached fragment": PORTAL.replace(RECORD["new"], "", 1) + "\n" + RECORD["new"],
    "misplaced inside the correct function": PORTAL.replace(RECORD["new"], "", 1).replace(
        INTRO, INTRO + RECORD["new"], 1
    ),
    "wrong function owner": PORTAL.replace(OWNER, "  function UNREVIEWED(", 1),
    "duplicate function owner": PORTAL + "\n" + OWNER + ") {\n  }\n",
    "extra old metrics outside conditional": PORTAL + "\n" + RECORD["old"],
    "recognizable partial fragment": BEFORE[PORTAL_FILE] + "\n${canBrowse ? `<dl",
    "standalone fragment without owner": RECORD["new"],
}


@pytest.mark.parametrize("name", PORTAL_CASES)
def test_portal_inverse_rejects_unreviewed_owned_conditional(name):
    bad = PORTAL_CASES[name]
    assert bad != PORTAL
    with pytest.raises(AssertionError, match="Unreviewed Gallery readability"):
        project(bad, PORTAL_FILE)
