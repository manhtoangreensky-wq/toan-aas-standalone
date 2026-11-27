"""Pressure the finite Python convergence leaf without importing application code."""

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from tests.helpers.gallery_native_historical import gallery_native_historical_source as inverse


ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "29e0c154dfd247ac4b0a68cd6336ec83fb3af8ef"
PORTAL, I18N, INTEGRATION = (
    "static/portal/portal.js", "static/portal/portal-i18n.js", "static/portal/integration.js",
)
FILES = [PORTAL, I18N, INTEGRATION, "copyfast_free_prompt_gallery.py", "copyfast_memory.py"]
FIXTURES = [
    json.loads((ROOT / "tests/fixtures" / name).read_bytes())
    for name in ("gallery-native-history.json", "gallery-native-transport-history.json",
                 "gallery-native-backend-history.json")
]
RECORDS = {file: [row for fixture in FIXTURES for row in fixture["records"] if row["file"] == file]
           for file in FILES}
BASE = {
    file: subprocess.run(["git", "show", f"{BASE_SHA}:{file}"], cwd=ROOT, check=True,
                         stdout=subprocess.PIPE).stdout.decode("utf-8").replace("\r\n", "\n")
    for file in FILES
}
STAGES = {}
for _file in FILES:
    _stages = [BASE[_file]]
    for _row in RECORDS[_file]:
        assert _stages[-1].count(_row["before"]) == 1, "Independent forward reconstruction anchor"
        _stages.append(_stages[-1].replace(_row["before"], _row["after"], 1))
    STAGES[_file] = _stages
CURRENT = {file: stages[-1] for file, stages in STAGES.items()}
CASES = [(file, index) for file in FILES for index in range(len(RECORDS[file]))]


def digest(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def piece(file: str, index: int) -> str:
    row = RECORDS[file][index]
    if file == I18N:
        return row["after"][:-len(row["before"])]
    value = row["after"]
    for later in RECORDS[file][index + 1:]:
        if later["before"] in value:
            assert value.count(later["before"]) == 1
            value = value.replace(later["before"], later["after"], 1)
    assert CURRENT[file].count(value) == 1, "Owned descendant must remain unique in actual final source"
    return value


def reject(source: str, file: str) -> None:
    with pytest.raises(ValueError, match="Unreviewed Gallery native"):
        inverse(source, file)


@pytest.mark.parametrize("file", FILES)
def test_independent_git_base_is_exact_noop_identity(file):
    assert inverse(BASE[file], file) is BASE[file]


@pytest.mark.parametrize("file", FILES)
def test_actual_full_source_is_exact_locked_construction_and_inverse_equals_git_base(file):
    actual = (ROOT / file).read_bytes().decode("utf-8").replace("\r\n", "\n")
    assert digest(actual) == digest(CURRENT[file])
    assert inverse(actual, file) == BASE[file]


@pytest.mark.parametrize("file", FILES)
def test_inverse_is_idempotent(file):
    once = inverse(CURRENT[file], file)
    assert inverse(once, file) is once


@pytest.mark.parametrize("file", FILES)
def test_unknown_prefix_suffix_unicode_and_crlf_bytes_survive(file):
    prefix = '/* UNKNOWN freePromptGallery.taxonomy.fake 客户 */\r\n'
    suffix = '\n# UNKNOWN feedback.customer 25% {unchanged}\r\n'
    assert inverse(prefix + CURRENT[file] + suffix, file) == prefix + BASE[file] + suffix


@pytest.mark.parametrize("file", FILES)
def test_unknown_interior_delta_remains_visible_to_the_original_pin(file):
    anchor = '  "use strict";' if file.endswith(".js") else "from __future__ import annotations"
    addition = "\n# UNRELATED 客户原文 25% {keep_me}\r\n"
    assert CURRENT[file].count(anchor) == BASE[file].count(anchor) == 1
    actual = inverse(CURRENT[file].replace(anchor, anchor + addition, 1), file)
    assert actual == BASE[file].replace(anchor, anchor + addition, 1)
    assert digest(actual) != digest(BASE[file])


@pytest.mark.parametrize("file", FILES)
def test_no_signal_arbitrary_source_is_unchanged(file):
    source = 'customer="freePromptGallery.taxonomy.fake";\r\n客户原文25%'
    assert inverse(source, file) is source


@pytest.mark.parametrize("file,index", CASES)
def test_deleting_each_final_owned_record_fails_closed(file, index):
    reject(CURRENT[file].replace(piece(file, index), "", 1), file)


@pytest.mark.parametrize("file,index", CASES)
def test_changed_bytes_in_each_owned_record_fail_closed(file, index):
    owned = piece(file, index)
    at = len(owned) // 2
    changed = owned[:at] + "UNREVIEWED" + owned[at + 1:]
    reject(CURRENT[file].replace(owned, changed, 1), file)


@pytest.mark.parametrize("file,index", CASES)
def test_duplicate_exact_owned_record_fails_closed(file, index):
    reject(CURRENT[file] + "\n" + piece(file, index), file)


@pytest.mark.parametrize("file,index", CASES)
def test_detached_record_before_its_approved_owner_fails_closed(file, index):
    owned = piece(file, index)
    reject(owned + "\n" + CURRENT[file].replace(owned, "", 1), file)


@pytest.mark.parametrize("file,index", CASES)
def test_partial_revert_of_each_owned_record_fails_closed(file, index):
    replacement = "" if file == I18N else RECORDS[file][index]["before"]
    reject(CURRENT[file].replace(piece(file, index), replacement, 1), file)


@pytest.mark.parametrize("file,stage", [
    (file, stage) for file in FILES for stage in range(1, len(RECORDS[file]))
])
def test_each_incomplete_proposal_round_is_not_final(file, stage):
    reject(STAGES[file][stage], file)


@pytest.mark.parametrize("file", ["foreign", "portal.js", "copyfast_gallery_locale.py",
                                  "static/portal/integration.js.bak"])
def test_foreign_file_is_noop_even_for_malformed_owned_source(file):
    source = CURRENT[PORTAL].replace("freePromptGalleryTaxonomyLabel", "BROKEN", 1)
    assert inverse(source, file) is source


@pytest.mark.parametrize("file,before", [
    (PORTAL, "  function freePromptGalleryListingState("),
    (PORTAL, "  function renderFreePromptGallerySaveResult("),
    (I18N, "  verifyEqualKeysets();"),
    (I18N, "  function deepFreeze(value) {"),
    (INTEGRATION, "  async function handleAction(event) {"),
    (INTEGRATION, "  function freePromptGalleryCatalogIsSafe("),
    ("copyfast_free_prompt_gallery.py", "from fastapi.responses import JSONResponse"),
    ("copyfast_free_prompt_gallery.py", "def _boundaries("),
    ("copyfast_memory.py", "def _gallery_memory_boundaries("),
    ("copyfast_memory.py", "async def create_note("),
])
def test_changed_required_owner_or_slot_anchor_fails_closed(file, before):
    assert CURRENT[file].count(before) == 1
    reject(CURRENT[file].replace(before, "UNREVIEWED_OWNER" + before[1:], 1), file)


@pytest.mark.parametrize("file", [PORTAL, INTEGRATION, "copyfast_memory.py"])
def test_complete_owned_function_nested_in_its_previous_owner_fails_closed(file):
    index = 0 if file == PORTAL else 1
    owned = piece(file, index)
    source = CURRENT[file].replace(owned, "", 1)
    if file == PORTAL:
        previous = source.index("  function freePromptGalleryListingState(")
        boundary = source.index("\n  }\n", previous)
    elif file == INTEGRATION:
        previous = source.index("  function freePromptGalleryCatalogIsSafe(")
        boundary = source.index("\n  }\n", previous)
    else:
        previous = source.index("def _gallery_memory_boundaries(")
        boundary = source.index("    return boundaries", previous)
    reject(source[:boundary] + "\n" + owned + source[boundary:], file)


def test_i18n_complete_blocks_assigned_to_foreign_locale_owner_fail_closed():
    owned = piece(I18N, 1)
    reject(CURRENT[I18N].replace(owned, owned.replace("MESSAGES.vi", "MESSAGES.fr", 1), 1), I18N)


def test_backend_partial_save_under_unrelated_top_level_owner_fails_closed():
    file = "copyfast_memory.py"
    owned = piece(file, 2)
    source = CURRENT[file].replace(owned, "", 1)
    previous = source.index("async def create_note(")
    following = source.index("    def operation(conn: Any) -> dict[str, Any]:", previous)
    reject(source[:following] + "def unrelated_owner():\n" + owned + "\n" + source[following:], file)


@pytest.mark.parametrize("file", FILES)
def test_non_string_source_is_rejected_before_target_dispatch(file):
    with pytest.raises(ValueError, match="string source"):
        inverse(None, file)
