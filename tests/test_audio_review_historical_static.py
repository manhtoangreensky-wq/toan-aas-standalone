"""Pressure finite Python ARF history; current151 BASE+11 forward acceptance stays Node-only."""
from pathlib import Path
import re
import runpy
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = runpy.run_path(str(ROOT / "tests/helpers/audio_review_historical_static.py"))
project, fail, groups = HELPER["historical_audio_review_source"], HELPER["FAIL"], HELPER["GROUPS"]
files = HELPER["FILES"]
actual = {file: (ROOT / file).read_text(encoding="utf8").replace("\r\n", "\n") for file in files}
baseline = {
    file: subprocess.check_output(["git", "show", HELPER["FIXTURE"]["base"] + ":" + file],
                                  cwd=ROOT).decode("utf8").replace("\r\n", "\n")
    for file in files
}


@pytest.mark.parametrize("file", files)
def test_arf_python_source_restores_exact_base_is_idempotent_and_keeps_outside_bytes(file):
    first, last = "/* CUSTOMER <img>& outside prefix */\n", "\n/* CUSTOMER outside tail */"
    assert project(actual[file], file) == baseline[file]
    assert project(baseline[file], file) is baseline[file]
    assert project(project(actual[file], file), file) == baseline[file]
    assert project(first + actual[file] + last, file) == first + baseline[file] + last
    assert project(first + last, file) == first + last
    assert project(actual[file], "customer/unrelated.js") is actual[file]


@pytest.mark.parametrize("index", range(5))
@pytest.mark.parametrize("kind", ["changed", "partial", "duplicate", "moved", "owner", "next"])
def test_arf_python_source_rejects_malformed_owned_region(index, kind):
    group = groups[index]
    source = actual[group["file"]]
    if kind == "changed":
        changed = group["new"].replace("review", "unreviewed", 1)
        assert changed != group["new"]
        malformed = source.replace(group["new"], changed, 1)
    elif kind == "partial":
        malformed = source.replace(group["new"], group["new"][:len(group["new"]) // 2], 1)
    elif kind == "duplicate":
        malformed = source + "\n" + group["new"]
    elif kind == "moved":
        malformed = source.replace(group["new"], "", 1) + "\n" + group["new"]
    elif kind == "owner":
        malformed = source.replace(group["owner"], group["owner"] + " UNREVIEWED", 1)
    else:
        changed = re.sub(r"\S", "X", group["next"], count=1)
        assert changed != group["next"]
        malformed = source.replace(group["next"], changed, 1)
    with pytest.raises(AssertionError, match=fail):
        project(malformed, group["file"])


@pytest.mark.parametrize("index", range(3))
def test_arf_python_source_rejects_mixed_old_and_current_integration(index):
    group = groups[index]
    malformed = actual[group["file"]].replace(group["new"], group["old"], 1)
    with pytest.raises(AssertionError, match=fail):
        project(malformed, group["file"])


@pytest.mark.parametrize("rename_calls", [False, True])
def test_arf_python_source_detects_renderer_only_patch_without_its_helper(rename_calls):
    file = "static/portal/portal.js"
    group = next(row for row in groups if row["file"] == file)
    helper = group["new"][:group["new"].index(group["oldOwner"])]
    malformed = actual[file].replace(helper, "", 1)
    assert HELPER["CONTRACT"]["renderer"]["new"] in malformed
    if rename_calls:
        malformed = malformed.replace("audioHubReviewSourceText", "UNKNOWN_DISPLAY")
    with pytest.raises(AssertionError, match=fail):
        project(malformed, file)


def test_arf_python_source_rejects_catalogue_append_outside_verify_and_freeze_fences():
    file = "static/portal/portal-i18n.js"
    group = next(row for row in groups if row["file"] == file)
    without = actual[file].replace(group["new"], "", 1)
    before_verify = without.replace("  function verifyEqualKeysets() {",
                                    group["new"] + "\n  function verifyEqualKeysets() {", 1)
    for malformed in [before_verify, without + "\n" + group["new"]]:
        with pytest.raises(AssertionError, match=fail):
            project(malformed, file)


@pytest.mark.parametrize("name,file,function", [
    ("media_fixed_feedback", "static/portal/integration.js", "historical_media_fixed_feedback_integration"),
    ("media_detail", "static/portal/portal.js", "historical_media_detail_portal"),
])
def test_arf_python_source_composes_with_older_finite_leaf_without_changing_its_baseline(name, file, function):
    older = runpy.run_path(str(ROOT / f"tests/helpers/{name}_historical_static.py"))
    expected = subprocess.check_output(["git", "show", older["FIXTURE"]["base"] + ":" + file],
                                       cwd=ROOT).decode("utf8").replace("\r\n", "\n")
    assert older[function](actual[file]) == expected
    assert older[function](project(actual[file], file)) == expected


@pytest.mark.parametrize("kind", ["outside_helper", "overlapping_catch"])
def test_arf_python_source_keeps_older_mff_error_identity_after_reviewed_input_strip(kind):
    file = "static/portal/integration.js"
    source = project(actual[file], file) if kind == "overlapping_catch" else actual[file]
    marker = ("      const editorialError = " if kind == "overlapping_catch"
              else "  function mediaWorkspaceFeedbackText(key, fallback) {")
    malformed = source.replace(marker, marker + " /* MFF malformed outside ARF ownership */", 1)
    stripped = project(malformed, file)
    assert "/* MFF malformed outside ARF ownership */" in stripped
    older = runpy.run_path(str(ROOT / "tests/helpers/media_fixed_feedback_historical_static.py"))
    with pytest.raises(AssertionError, match=older["FAIL"]):
        older["historical_media_fixed_feedback_integration"](malformed)


@pytest.mark.parametrize("source", [None, 1, [], {}, b"source"])
def test_arf_python_source_rejects_wrong_source_type(source):
    with pytest.raises(AssertionError, match=fail):
        project(source, files[0])


@pytest.mark.parametrize("file", [None, 1, [], {}, b"file"])
def test_arf_python_source_rejects_wrong_file_type(file):
    with pytest.raises(AssertionError, match=fail):
        project(actual[files[0]], file)
