"""Verify the visual compatibility layer without masking source changes."""
from pathlib import Path
import runpy
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = runpy.run_path(str(ROOT / "tests/helpers/audio_review_visual_historical_static.py"))
project, contract, fail = HELPER["historical_audio_review_visual_source"], HELPER["CONTRACT"], HELPER["FAIL"]


@pytest.mark.parametrize("file", ["static/portal/portal.js", "static/portal/portal-i18n.js"])
def test_visual_projection_restores_base_and_preserves_unrelated_bytes(file):
    current = (ROOT / file).read_text(encoding="utf8").replace("\r\n", "\n")
    base = subprocess.check_output(["git", "show", contract["base"] + ":" + file], cwd=ROOT).decode("utf8").replace("\r\n", "\n")
    assert project(current, file) == base
    assert project(base, file) == base
    assert project("/* customer */\n" + current, file) == "/* customer */\n" + base
    for row in [row for row in contract["records"] if row["file"] == file]:
        malformed = row["new"].replace("reference file", "UNREVIEWED", 1) if file.endswith("portal-i18n.js") else ""
        with pytest.raises(AssertionError, match=fail):
            project(current.replace(row["new"], malformed, 1), file)
        with pytest.raises(AssertionError, match=fail):
            project(current + "\n" + row["new"], file)
