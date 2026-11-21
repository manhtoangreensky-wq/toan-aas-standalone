"""Finite historical integration input only; never current-source acceptance."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
RAW = (ROOT / "tests/fixtures/media-fixed-feedback-reviewed.json").read_bytes()
FAIL = "Unreviewed media fixed feedback historical source"
assert hashlib.sha256(RAW).hexdigest() == "808d89af0587a53a13bb78e83be5e8fab6f6e7e98240183b9966766ae5febfa6", FAIL
FIXTURE = json.loads(RAW)
GROUPS = [row for row in FIXTURE["historicalFragments"] if row["file"] == "static/portal/integration.js"]
assert len(GROUPS) == 8 and FIXTURE["base"] == "6f04b8449d7354ca44397c199ccdda77107f577e", FAIL


def historical_media_fixed_feedback_integration(source: str) -> str:
    assert isinstance(source, str), FAIL
    markers = ("mediaWorkspaceFeedbackText", "mediaWorkspaceErrorText", "audioWorkspace.feedback.")
    if not any(marker in source for marker in markers):
        return source
    for group in GROUPS:
        owner, following = group["owner"], group["next"]
        assert source.count(owner) == source.count(following) == 1, FAIL + " unique owner"
        start, end = source.index(owner), source.index(following)
        assert end > start and source[start:end] == group["new"], FAIL + " complete bounded region"
        assert source.count(group["new"]) == 1, FAIL + " unique current region"
    for group in reversed(GROUPS):
        source = source.replace(group["new"], group["old"], 1)
    assert not any(marker in source for marker in markers), FAIL + " detached marker"
    return source
