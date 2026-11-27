"""Pressure the AGC Python inverse with independent Git source, never app imports."""

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from tests.helpers.admin_guard_customer_copy_historical import (
    admin_guard_customer_copy_historical_source as inverse,
)


ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "5f316f29c9b8657c4018f5174c4c4ce4f16c1e5f"
FIXTURE = json.loads((ROOT / "tests/fixtures/admin-guard-customer-copy-history.json").read_bytes())
FILES = ["static/portal/portal.js", "static/portal/portal-i18n.js"]
BASE = {
    file: subprocess.run(["git", "show", f"{BASE_SHA}:{file}"], cwd=ROOT, check=True,
                         stdout=subprocess.PIPE).stdout.decode("utf-8").replace("\r\n", "\n")
    for file in FILES
}
STAGES = {}
for _file in FILES:
    _stages = [BASE[_file]]
    for _row in [row for row in FIXTURE["records"] if row["file"] == _file]:
        assert _stages[-1].count(_row["before"]) == 1, "Independent proposal reconstruction anchor"
        _stages.append(_stages[-1].replace(_row["before"], _row["after"], 1))
    STAGES[_file] = _stages
CURRENT = {file: stages[-1] for file, stages in STAGES.items()}
RECORD_IDS = [f"{index}-{row['task']}" for index, row in enumerate(FIXTURE["records"])]
OWNERS = FIXTURE["owners"]


def digest(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def piece(row):
    if row["after"]:
        return row["after"]
    return next(owner["after"] for owner in OWNERS
                if owner["file"] == row["file"] and owner["name"] == "renderSupportAdminBase")


def old_piece(row):
    if row["after"]:
        return row["before"]
    return next(owner["before"] for owner in OWNERS
                if owner["file"] == row["file"] and owner["name"] == "renderSupportAdminBase")


def reject(source, file):
    with pytest.raises(ValueError, match="Unreviewed Admin guard customer copy history"):
        inverse(source, file)


@pytest.mark.parametrize("file", FILES)
def test_immutable_git_base_is_byte_exact_identity_noop(file):
    assert inverse(BASE[file], file) is BASE[file]


@pytest.mark.parametrize("file", FILES)
def test_actual_current_is_exact_proposal_construction_and_inverse_equals_independent_git_base(file):
    physical = (ROOT / file).read_bytes().decode("utf-8").replace("\r\n", "\n")
    metadata = next(row for row in FIXTURE["application_sources"] if row["file"] == file)
    assert digest(physical) == metadata["current_lf_sha256"]
    assert physical == CURRENT[file]
    assert digest(BASE[file]) == metadata["base_lf_sha256"]
    assert inverse(physical, file) == BASE[file]


@pytest.mark.parametrize("file", FILES)
def test_projection_is_idempotent(file):
    once = inverse(CURRENT[file], file)
    assert inverse(once, file) is once


@pytest.mark.parametrize("file", FILES)
def test_unknown_prefix_suffix_customer_unicode_and_crlf_bytes_are_preserved(file):
    prefix = "/* UNKNOWN α 客户 <b>literal</b> 25% */\r\n"
    suffix = "\n/* ADMIN_SUPPORT_COPY_CUSTOM untouched */\r\n"
    assert inverse(prefix + CURRENT[file] + suffix, file) == prefix + BASE[file] + suffix


@pytest.mark.parametrize("file", FILES)
def test_unknown_interior_delta_is_not_masked_from_existing_historical_pin(file):
    anchor = '  "use strict";'
    addition = "\n  /* UNKNOWN_CUSTOMER_TEXT 客户原文 25% */"
    actual = inverse(CURRENT[file].replace(anchor, anchor + addition, 1), file)
    assert actual == BASE[file].replace(anchor, anchor + addition, 1)
    assert digest(actual) != digest(BASE[file])


@pytest.mark.parametrize("file", FILES)
def test_no_signal_arbitrary_source_preserves_identity(file):
    source = 'const customer = "ADMIN_SUPPORT_COPY_CUSTOM";\r\n客户文字'
    assert inverse(source, file) is source


@pytest.mark.parametrize("row", FIXTURE["records"], ids=RECORD_IDS)
@pytest.mark.parametrize("mutation", ["partial", "changed", "deleted", "duplicate", "detached"])
def test_every_approved_record_rejects_malformed_or_mixed_source(row, mutation):
    file, owned = row["file"], piece(row)
    if mutation == "partial":
        source = CURRENT[file].replace(owned, old_piece(row), 1)
    elif mutation == "changed":
        at = len(owned) // 2
        changed = owned[:at] + "UNREVIEWED_BAD_COPY" + owned[at + 1:]
        source = CURRENT[file].replace(owned, changed, 1)
    elif mutation == "deleted":
        source = CURRENT[file].replace(owned, "", 1)
    elif mutation == "duplicate":
        source = CURRENT[file] + "\n" + owned
    else:
        source = owned + "\n" + CURRENT[file].replace(owned, "", 1)
    reject(source, file)


@pytest.mark.parametrize("row", OWNERS, ids=lambda row: row["name"])
@pytest.mark.parametrize("mutation", ["function_wrapper", "if_wrapper", "detached", "previous",
                                     "following", "duplicate_declaration", "inside_owner"])
def test_each_frozen_owner_enforces_context_placement_and_identity(row, mutation):
    file, owned, slot = row["file"], row["after"], row["slot"]
    if mutation == "function_wrapper":
        source = CURRENT[file].replace(owned, "  function foreignAgcOwner() {\n" + owned + "  }\n", 1)
    elif mutation == "if_wrapper":
        source = CURRENT[file].replace(owned, "  if (foreignCondition) {\n" + owned + "  }\n", 1)
    elif mutation == "detached":
        source = owned + "\n" + CURRENT[file].replace(owned, "", 1)
    elif mutation in {"previous", "following"}:
        marker = slot[mutation]
        source = CURRENT[file].replace(marker, "BROKEN_OWNER" + marker[1:], 1)
    elif mutation == "duplicate_declaration":
        source = CURRENT[file] + "\n" + slot["declaration"]
    else:
        changed = owned.replace("\n", "\n/* UNKNOWN_INSIDE_OWNER */\n", 1)
        source = CURRENT[file].replace(owned, changed, 1)
    reject(source, file)


@pytest.mark.parametrize("row", OWNERS, ids=lambda row: row["name"])
def test_context_gap_preserves_comments_and_quoted_declaration_like_text(row):
    addition = '  /* {\n  function foreignAgcOwner() {\n  const foreign = 1;\n  } */\r\n  "class foreign { }";\n'
    source = CURRENT[row["file"]].replace(row["after"], addition + row["after"], 1)
    expected = BASE[row["file"]].replace(row["before"], addition + row["before"], 1)
    assert inverse(source, row["file"]) == expected


@pytest.mark.parametrize("row", [row for row in OWNERS if row["slot"]["kind"] == "function"],
                         ids=lambda row: row["name"])
def test_owner_nested_before_previous_function_closes_fails_closed(row):
    source = CURRENT[row["file"]].replace(row["after"], "", 1)
    previous = source.index(row["slot"]["previous"])
    close = source.index("\n  }\n", previous)
    assert close > previous
    reject(source[:close] + "\n" + row["after"] + source[close:], row["file"])


@pytest.mark.parametrize("declaration", [
    "function foreignAgcOwner() {}", "const foreignAgcOwner = 1;",
    "let foreignAgcOwner = 1;", "class foreignAgcOwner {}",
])
def test_context_gap_rejects_intervening_real_top_level_declaration(declaration):
    row = OWNERS[0]
    reject(CURRENT[row["file"]].replace(row["after"], "  " + declaration + "\n" + row["after"], 1), row["file"])


@pytest.mark.parametrize("file", FILES)
def test_reordered_complete_owners_fail_closed(file):
    a, b = [row["after"] for row in OWNERS if row["file"] == file][:2]
    source = CURRENT[file].replace(a, "AGC_SWAP_SENTINEL", 1).replace(b, a, 1).replace("AGC_SWAP_SENTINEL", b, 1)
    reject(source, file)


@pytest.mark.parametrize("file,stage", [
    (file, stage) for file in FILES for stage in range(1, len(STAGES[file]) - 1)
])
def test_each_incomplete_proposal_round_fails_closed(file, stage):
    reject(STAGES[file][stage], file)


def test_mutated_guard_condition_is_not_masked_by_projection():
    row = next(row for row in OWNERS if row["name"] == "actionBlockReason")
    changed = row["after"].replace("context.session.authenticated !== true", "context.session.authenticated === true", 1)
    assert changed != row["after"]
    reject(CURRENT[row["file"]].replace(row["after"], changed, 1), row["file"])


def test_support_empty_removal_cannot_mask_new_unreviewed_boundary():
    row = next(row for row in OWNERS if row["name"] == "renderSupportAdminBase")
    changed = row["after"].replace("</article>", "<section>UNREVIEWED_BOUNDARY</section></article>", 1)
    assert changed != row["after"]
    reject(CURRENT[row["file"]].replace(row["after"], changed, 1), row["file"])


@pytest.mark.parametrize("file", ["portal.js", "foreign", "static/portal/integration.js"])
def test_foreign_filename_preserves_malformed_source_identity(file):
    source = CURRENT[FILES[0]].replace("actionBlockReason", "BROKEN", 1)
    assert inverse(source, file) is source


@pytest.mark.parametrize("file", [*FILES, "foreign"])
def test_non_string_source_raises_value_error_before_dispatch(file):
    with pytest.raises(ValueError, match="Unreviewed Admin guard customer copy history: string source"):
        inverse(None, file)
