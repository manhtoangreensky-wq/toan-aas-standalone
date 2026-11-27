"""Exercise the Python Gallery leaf with independently frozen source records."""
from pathlib import Path
import json
import subprocess
import pytest
from tests.helpers.gallery_customer_copy_historical import gallery_customer_copy_historical_source as project

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/gallery-customer-copy.json").read_bytes())
FILES = [row["file"] for row in FIXTURE["applicationSources"]]
BEFORE, CURRENT = {}, {}
for file in FILES:
    BEFORE[file] = subprocess.check_output(["git", "show", FIXTURE["base_sha"] + ":" + file], cwd=ROOT).decode().replace("\r\n", "\n")
    source = BEFORE[file]
    for row in [row for row in FIXTURE["records"] if row["file"] == file]:
        assert source.count(row["old"]) == 1
        source = source.replace(row["old"], row["new"], 1)
    CURRENT[file] = source


@pytest.mark.parametrize("file", FILES)
def test_gallery_inverse_restores_base_and_preserves_unknown_bytes(file):
    assert project(CURRENT[file], file) == BEFORE[file]
    assert project(project(CURRENT[file], file), file) == BEFORE[file]
    assert project(BEFORE[file], file) is BEFORE[file]
    assert project("/* CUSTOMER */\r\n" + CURRENT[file] + "\r\n/* TAIL */", file) == "/* CUSTOMER */\r\n" + BEFORE[file] + "\r\n/* TAIL */"
    assert project(CURRENT[file], "customer/unrelated.js") is CURRENT[file]


@pytest.mark.parametrize("file", FILES)
@pytest.mark.parametrize("kind", ["changed", "partial", "duplicate", "detached", "owner", "reordered"])
def test_gallery_inverse_rejects_unreviewed_owned_region(file, kind):
    records = [row for row in FIXTURE["records"] if row["file"] == file]
    row = records[len(records) // 2]
    source = CURRENT[file]
    if kind == "changed":
        bad = source.replace(row["new"], row["new"].replace("freePromptGallery", "UNREVIEWED"), 1)
    elif kind == "partial":
        bad = source.replace(row["new"], row["old"], 1)
    elif kind == "duplicate":
        bad = source + "\n" + row["new"]
    elif kind == "detached":
        bad = source.replace(row["new"], "", 1) + "\n" + row["new"]
    elif kind == "owner":
        owner = "  const " + row["owner"] + " = {" if row["kind"] == "copy" else "  function " + row["owner"] + "("
        bad = source.replace(owner, "  const UNKNOWN = {" if row["kind"] == "copy" else "  function UNKNOWN(", 1)
    else:
        other = next(value for value in records if value is not row)
        bad = source.replace(row["new"], "__GPC_SWAP__", 1).replace(other["new"], row["new"], 1).replace("__GPC_SWAP__", other["new"], 1)
    assert bad != source
    with pytest.raises(AssertionError, match="Unreviewed Gallery customer copy"):
        project(bad, file)
