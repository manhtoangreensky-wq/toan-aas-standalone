"""Pressure the finite pending-feedback historical projection."""
from pathlib import Path
import runpy
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = runpy.run_path(str(ROOT / "tests/helpers/audio_review_pending_historical_static.py"))
project, contract, fail = HELPER["historical_audio_review_pending_source"], HELPER["CONTRACT"], HELPER["FAIL"]
files = ["static/portal/integration.js", "static/portal/portal-i18n.js"]
baseline = {file: subprocess.check_output(["git", "show", contract["base"] + ":" + file], cwd=ROOT)
            .decode("utf8").replace("\r\n", "\n") for file in files}
candidate = {file: (ROOT / file).read_text(encoding="utf8").replace("\r\n", "\n") for file in files}


@pytest.mark.parametrize("file", files)
def test_projection_restores_exact_base_and_preserves_outside_bytes(file):
    assert project(candidate[file], file) == baseline[file]
    assert project(baseline[file], file) == baseline[file]
    assert project("/* customer */\n" + candidate[file], file) == "/* customer */\n" + baseline[file]
    assert project(candidate[file], "customer/unrelated.js") == candidate[file]


@pytest.mark.parametrize("index", range(3))
def test_projection_rejects_altered_or_duplicated_records(index):
    row = contract["records"][index]
    changed = (row["new"].replace("throw error;", "throw new Error('altered');", 1) if index == 0
               else row["new"].replace("review.", "unreviewed.", 1))
    assert changed != row["new"]
    with pytest.raises(AssertionError, match=fail):
        project(candidate[row["file"]].replace(row["new"], changed, 1), row["file"])
    with pytest.raises(AssertionError, match=fail):
        project(candidate[row["file"]] + "\n" + row["new"], row["file"])
