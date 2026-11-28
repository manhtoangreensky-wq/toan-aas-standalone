"""Pressure checks for the finite Python historical source input."""
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from tests.helpers.customer_language_cleanup_historical import customer_language_historical_source as inverse

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "tests/fixtures/customer-language-cleanup-history.json").read_text(encoding="utf-8"))
FILES = ("static/portal/portal.js", "static/portal/portal-i18n.js")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@pytest.mark.parametrize("file", FILES)
def test_exact_epoch_recovery_preserves_foreign_content_and_line_endings(file):
    before = subprocess.check_output(["git", "show", f"{FIXTURE['base_sha']}:{file}"], cwd=ROOT).decode().replace("\r\n", "\n")
    after = (ROOT / file).read_text(encoding="utf-8")
    foreign = "\n/* Khách giữ QA Studio Facebook TikTok <b>& */\n"
    assert digest(inverse(after, file)) == digest(before)
    assert inverse(before, file) == before
    assert digest(inverse(inverse(after, file), file)) == digest(before)
    assert digest(inverse(after + foreign, file)) == digest(before + foreign)
    assert digest(inverse(after.replace("\n", "\r\n"), file)) == digest(before.replace("\n", "\r\n"))
    assert inverse("foreign source", "not-owned.py") == "foreign source"


@pytest.mark.parametrize("file", FILES)
def test_each_owned_record_rejects_missing_changed_or_duplicate_content(file):
    # Isolate the complete real record set without retaining full-bundle
    # tracebacks for each rejected mutation on memory-constrained Windows.
    # The current physical bundle is checked in the recovery test above.
    after = "\n".join(row["after"] for row in FIXTURE["records"] if row["file"] == file)
    for row in FIXTURE["records"]:
        if row["file"] != file:
            continue
        assert after.count(row["after"]) == 1
        position = next(i for i, char in enumerate(row["after"]) if not char.isspace())
        changed = row["after"][:position + 1] + "_CHANGED" + row["after"][position + 1:]
        for replacement in ("", changed, row["after"] + row["after"]):
            with pytest.raises(AssertionError, match="Unreviewed customer language"):
                inverse(after.replace(row["after"], replacement, 1), file)
