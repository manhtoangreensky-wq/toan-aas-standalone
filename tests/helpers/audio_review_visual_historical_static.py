"""Finite visual-source projection for earlier historical checks only."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / "tests/fixtures/audio-review-visual-contract.json").read_bytes())
FAIL = "Unreviewed audio review visual"
assert CONTRACT["base"] == "ea4da7c446059f911f3b59d61f9f92f63ea95c94" and len(CONTRACT["records"]) == 3, FAIL


def historical_audio_review_visual_source(source: str, file: str) -> str:
    assert isinstance(source, str) and isinstance(file, str), FAIL
    records = [row for row in CONTRACT["records"] if row["file"] == file]
    if not records:
        return source
    markers = (("page.layout === \"audio-hub-detail\" ? audioWorkspaceText('workspace.hubLabel'",
                'audioWorkspaceText(count === 1 ? "review.reference"')
               if file.endswith("portal.js") else ('"audioWorkspace.review.reference"',))
    if not any(marker in source for marker in markers):
        return source
    for row in records:
        assert source.count(row["new"]) == 1, FAIL + " exact current record"
        if row["old"] not in row["new"]:
            assert source.count(row["old"]) == 0, FAIL + " mixed previous record"
    for row in records:
        source = source.replace(row["new"], row["old"], 1)
    assert not any(marker in source for marker in markers), FAIL + " detached marker"
    return source
