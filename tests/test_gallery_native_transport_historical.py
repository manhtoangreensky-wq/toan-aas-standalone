"""Pressure tests for the finite transport-input projection, without app imports."""

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from tests.helpers.gallery_native_transport_historical import (
    gallery_native_transport_historical_source as inverse,
)
from tests.helpers.auth_return_historical import auth_return_historical_source
from tests.helpers.document_natural_copy_historical import document_natural_historical_source


ROOT = Path(__file__).resolve().parents[1]
TARGET = "static/portal/integration.js"
BASE_SHA = "29e0c154dfd247ac4b0a68cd6336ec83fb3af8ef"
FIXTURE = json.loads((ROOT / "tests/fixtures/gallery-native-transport-history.json").read_bytes())
RECORDS = FIXTURE["records"]
BASE = subprocess.run(
    ["git", "show", f"{BASE_SHA}:{TARGET}"],
    cwd=ROOT, check=True, stdout=subprocess.PIPE,
).stdout.decode("utf-8").replace("\r\n", "\n")
STAGES = [BASE]
for record in RECORDS:
    previous = STAGES[-1]
    assert previous.count(record["before"]) == 1, "Independent forward reconstruction needs its exact predecessor"
    STAGES.append(previous.replace(record["before"], record["after"], 1))
CURRENT = STAGES[-1]


def digest(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def final_piece(index: int) -> str:
    """Follow an approved record through later overlapping full-block edits."""
    piece = RECORDS[index]["after"]
    for later in RECORDS[index + 1:]:
        if later["before"] in piece:
            assert piece.count(later["before"]) == 1
            piece = piece.replace(later["before"], later["after"], 1)
    assert CURRENT.count(piece) == 1, "Every tested historical owner must still have one final descendant"
    return piece


def reject(source: str, reason: str = "") -> None:
    with pytest.raises(ValueError, match="Unreviewed Gallery native transport history"):
        inverse(source)


def test_baseline_is_exact_noop_identity() -> None:
    assert inverse(BASE) is BASE
    assert digest(BASE) == "9b08a7f0421c0f27232b19bd006176cb5f6566b183c543e2f8d68ef5f4ba8945"


def test_eleven_record_inverse_restores_independently_read_git_base() -> None:
    assert digest(inverse(CURRENT)) == digest(BASE)
    assert len(inverse(CURRENT)) == len(BASE)


def test_physical_integration_is_exact_approved_final_and_restores_base() -> None:
    physical = (ROOT / TARGET).read_bytes().decode("utf-8").replace("\r\n", "\n")
    physical = document_natural_historical_source(physical, TARGET)
    physical = auth_return_historical_source(physical, TARGET)
    assert digest(physical) == "15fa2ba31745ccb4316f8d8c88b9a4d5fccf8a086273cce347780846667c28f1"
    assert digest(physical) == digest(CURRENT)
    assert digest(inverse(physical)) == digest(BASE)


def test_inverse_is_idempotent() -> None:
    once = inverse(CURRENT)
    assert inverse(once) is once
    assert digest(once) == digest(BASE)


def test_unknown_prefix_and_suffix_keep_exact_unicode_crlf_and_fake_prefix() -> None:
    prefix = '/* freePromptGalleryLocaleOwner_fake="客户原文"; 25% */\r\n'
    suffix = '\n/* FREE_PROMPT_GALLERY_FEEDBACK_VI_CUSTOM: α\r\nUNCHANGED */\r\n'
    assert digest(inverse(prefix + CURRENT + suffix)) == digest(prefix + BASE + suffix)


@pytest.mark.parametrize("needle", [
    '  "use strict";',
    "  async function api(path, options) {",
    "  function merge(next) {",
])
def test_unknown_interior_outside_owned_chunks_is_never_normalized(needle: str) -> None:
    addition = "\n    /* UNRELATED_DELTA 客户文字 25% {keep_me} */"
    assert CURRENT.count(needle) == 1 and BASE.count(needle) == 1
    changed = CURRENT.replace(needle, needle + addition, 1)
    expected = BASE.replace(needle, needle + addition, 1)
    actual = inverse(changed)
    assert digest(actual) == digest(expected)
    assert digest(actual) != digest(BASE), "Historical pin must still observe the unrelated delta"


@pytest.mark.parametrize("file", ["portal.js", "static/portal/portal.js", "static/portal/integration.js.bak", "foreign"])
def test_wrong_file_is_noop_even_with_malformed_owned_source(file: str) -> None:
    malformed = CURRENT.replace("freePromptGalleryLocaleOwner", "BROKEN_OWNER", 1)
    assert inverse(malformed, file) is malformed


def test_no_owned_signal_preserves_unknown_arbitrary_fake_prefix_source() -> None:
    source = 'const customer = "freePromptGalleryLocaleOwner_fake";\r\nconst FREE_PROMPT_GALLERY_FEEDBACK_VI_CUSTOM = "原样";'
    assert inverse(source) is source


@pytest.mark.parametrize("index", range(11), ids=lambda n: f"record-{n}")
def test_changed_bytes_inside_every_final_record_descendant_fail_closed(index: int) -> None:
    piece = final_piece(index)
    changed = piece.replace("freePromptGallery", "unreviewedGallery", 1)
    assert changed != piece
    reject(CURRENT.replace(piece, changed, 1), "changed owned bytes")


@pytest.mark.parametrize("index", range(11), ids=lambda n: f"record-{n}")
def test_partial_or_downgraded_owned_record_fails_closed(index: int) -> None:
    piece = final_piece(index)
    assert piece != RECORDS[index]["before"]
    reject(CURRENT.replace(piece, RECORDS[index]["before"], 1), "partial/downgraded")


@pytest.mark.parametrize("index", range(11), ids=lambda n: f"record-{n}")
def test_duplicate_whole_owned_record_fails_closed(index: int) -> None:
    reject(CURRENT + "\n" + final_piece(index), "duplicate")


@pytest.mark.parametrize("index", [0, 1, 2, 3, 4, 5, 6, 7, 8])
def test_detached_owned_record_outside_approved_slot_fails(index: int) -> None:
    piece = final_piece(index)
    reject(CURRENT.replace(piece, "", 1) + "\n" + piece, "detached")


@pytest.mark.parametrize("stage", range(1, 11), ids=lambda n: f"intermediate-{n}")
def test_every_incomplete_round_including_r1a_and_r2_is_rejected(stage: int) -> None:
    reject(STAGES[stage], "not the final complete sequence")


def test_reordered_complete_filter_and_items_functions_fail() -> None:
    a, b = final_piece(1), final_piece(2)
    source = CURRENT.replace(a, "GSC_SWAP_MARKER", 1).replace(b, a, 1).replace("GSC_SWAP_MARKER", b, 1)
    reject(source, "function order")


def test_reordered_complete_detail_and_save_action_branches_fail() -> None:
    a, b = final_piece(10), final_piece(8)
    source = CURRENT.replace(a, "GSC_SWAP_MARKER", 1).replace(b, a, 1).replace("GSC_SWAP_MARKER", b, 1)
    reject(source, "action order")


@pytest.mark.parametrize("before,after", [
    ("  async function handleAction(event) {", "  async function unrelatedAction(event) {"),
    ("  function freePromptGalleryCatalogIsSafe(", "  function detachedCatalogIsSafe("),
    ("  function guideCenterRequestIsCurrent(", "  function detachedGuideCurrent("),
    ("  let guideCenterSessionEpoch = 0;", "  let detachedGuideSessionEpoch = 0;"),
    ("      if (action === \"free-prompt-gallery-page\") {", "      if (action === \"unrelated-page\") {"),
])
def test_changed_required_owner_or_slot_anchor_is_not_accepted(before: str, after: str) -> None:
    assert CURRENT.count(before) == 1
    reject(CURRENT.replace(before, after, 1), "owner/slot")


def test_complete_function_nested_in_previous_function_fails_slot_validation() -> None:
    piece = final_piece(1)
    source = CURRENT.replace(piece, "", 1)
    previous = source.index("  function freePromptGalleryCatalogIsSafe(")
    end = source.index("\n  }\n", previous)
    source = source[:end] + "\n" + piece + source[end:]
    reject(source, "function nested within foreign owner")


def test_complete_action_detached_into_another_function_is_rejected() -> None:
    piece = final_piece(10)
    source = CURRENT.replace(piece, "", 1)
    foreign = source.index("  function merge(next) {")
    end = source.index("\n  }\n", foreign)
    source = source[:end] + "\n" + piece + source[end:]
    reject(source, "action under foreign owner")


def test_unknown_byte_inserted_between_owned_independent_functions_survives() -> None:
    piece = final_piece(2)
    addition = "  /* OUTSIDE_OWNED_FUNCTION native_custom 25% */\r\n"
    source = CURRENT.replace(piece, addition + piece, 1)
    expected = BASE.replace(RECORDS[2]["before"], addition + RECORDS[2]["before"], 1)
    assert digest(inverse(source)) == digest(expected)
