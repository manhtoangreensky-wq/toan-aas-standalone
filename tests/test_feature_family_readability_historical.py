"""Pressure the four-rule CSS inverse without changing application semantics."""
from pathlib import Path
import subprocess
import pytest
from tests.helpers.feature_family_readability_historical import (
    ADDITION, FILE, feature_family_readability_historical_source as project,
)
from tests.helpers.feature_catalog_full_bundle135_historical import feature_catalog_full_bundle135_historical_source as composed

ROOT = Path(__file__).resolve().parents[1]
BEFORE = subprocess.check_output(["git", "show", "363d6ca55081eea4089ebf489cd183b09ba1aa96:" + FILE], cwd=ROOT).decode().replace("\r\n", "\n")
CURRENT = BEFORE + ADDITION


def test_inverse_and_composition_preserve_base_and_unknown_bytes():
    assert project(CURRENT, FILE) == BEFORE
    assert project(project(CURRENT, FILE), FILE) == BEFORE
    assert composed(CURRENT, FILE) == BEFORE
    assert project(BEFORE, FILE) is BEFORE
    assert project("/* CUSTOMER */\r\n" + CURRENT + "\r\n/* TAIL */", FILE) == "/* CUSTOMER */\r\n" + BEFORE + "\r\n/* TAIL */"
    assert project(CURRENT, "other.css") is CURRENT
    assert project("", FILE) == ""


@pytest.mark.parametrize("kind", ["color", "theme", "partial", "duplicate", "detached", "declaration", "marker", "ancestor"])
def test_inverse_rejects_unreviewed_owned_rules(kind):
    mutations = {
        "color": CURRENT.replace(ADDITION, ADDITION.replace("var(--portal-text)", "red", 1)),
        "theme": CURRENT.replace(ADDITION, ADDITION.replace('html[data-portal-theme="dark"]', 'html:not([data-portal-theme="dark"])', 1)),
        "partial": CURRENT[:-40],
        "duplicate": CURRENT + ADDITION,
        "detached": BEFORE + "\n/* UNKNOWN */" + ADDITION,
        "declaration": CURRENT.replace(ADDITION, ADDITION.replace("color: var(--portal-text);", "color: var(--portal-text); opacity: .5;", 1)),
        "marker": CURRENT.replace("Keep family-directory text readable without changing surfaces or motion.", "UNKNOWN", 1),
        "ancestor": CURRENT.replace(ADDITION, ADDITION.replace('data-portal-presentation-route="default"', 'data-portal-presentation-route="features"', 1)),
    }
    with pytest.raises(AssertionError, match="Unreviewed feature-family readability"):
        project(mutations[kind], FILE)
