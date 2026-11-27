"""Exact finite Gallery readability inverse for historical QA, never runtime."""
from pathlib import Path
import hashlib
import json
from tests.helpers.feature_family_readability_historical import ADDITION as FAMILY_ADDITION

ROOT = Path(__file__).resolve().parents[2]
FAIL = "Unreviewed Gallery readability"
RAW = (ROOT / "tests/fixtures/gallery-readability.json").read_bytes().replace(b"\r\n", b"\n")
assert hashlib.sha256(RAW).hexdigest() == "3cfbd7b2618e05a11d91179d0b12d6be37d911e2d85ad495738defb0e00ab68f", FAIL
FIXTURE = json.loads(RAW)
assert FIXTURE["base_sha"] == "bf95e4017717622d694cbef02fde07799a823a8a", FAIL
assert len(FIXTURE["cssRules"]) == 11, FAIL
CSS_FILE = "static/portal/portal-theme.css"
ADDITION = "\n" + FIXTURE["cssMarker"] + "\n" + "\n".join(FIXTURE["cssRules"]) + "\n"
SELECTORS = [rule[:rule.index(" {")] for rule in FIXTURE["cssRules"]]
RECORD = FIXTURE["portalRecord"]
assert RECORD["file"] == "static/portal/portal.js" and RECORD["owner"] == "renderFreePromptGallery", FAIL
assert RECORD["new"] == "${canBrowse ? `" + RECORD["old"] + '` : ""}', FAIL
CONDITIONAL_OWNERS = ['${canBrowse ? `', "`" + RECORD["old"], RECORD["old"] + "`"]


def gallery_readability_historical_source(source: str, file: str) -> str:
    assert isinstance(source, str), FAIL
    if file == CSS_FILE:
        if FIXTURE["cssMarker"] not in source and not any(selector in source for selector in SELECTORS):
            return source
        assert source.count(FIXTURE["cssMarker"]) == 1, FAIL + " marker"
        for selector, rule in zip(SELECTORS, FIXTURE["cssRules"]):
            assert source.count(selector) == 1, FAIL + " selector owner"
            assert source.count(rule) == 1, FAIL + " exact rule"
        assert source.count(FAMILY_ADDITION) == 1, FAIL + " prior FCR anchor"
        assert source.count(ADDITION) == 1, FAIL + " exact eleven-rule addition"
        assert source.count(FAMILY_ADDITION + ADDITION) == 1, FAIL + " placement/order"
        return source.replace(ADDITION, "", 1)
    if file != RECORD["file"]:
        return source
    if RECORD["new"] not in source:
        assert not any(part in source for part in CONDITIONAL_OWNERS), FAIL + " changed conditional"
        return source
    owner = "  function " + RECORD["owner"] + "("
    start = source.find(owner)
    end = source.find("\n  }\n", start)
    at = source.find(RECORD["new"])
    assert start >= 0 and end > start and source.count(owner) == 1, FAIL + " function owner"
    assert source.count(RECORD["new"]) == 1, FAIL + " exact conditional"
    assert source.count(RECORD["old"]) == 1, FAIL + " unique metrics structure"
    assert start + len(owner) <= at and at + len(RECORD["new"]) <= end, FAIL + " conditional placement"
    intro = source.find('<section class="portal-content-prompt-pack-intro">', start)
    intro_end = source.find("</section>", intro)
    assert (
        intro >= start and intro_end < end and at > intro
        and at + len(RECORD["new"]) == intro_end and source[at - 10:at] == "</p></div>"
    ), FAIL + " intro metrics slot"
    assert all(source.count(part) == 1 for part in CONDITIONAL_OWNERS), FAIL + " conditional owner"
    return source.replace(RECORD["new"], RECORD["old"], 1)
