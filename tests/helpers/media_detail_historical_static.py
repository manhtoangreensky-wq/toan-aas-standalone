"""Finite newest historical input projection; never current-source acceptance."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
RAW = (ROOT / "tests/fixtures/media-detail-customer-copy-reviewed.json").read_bytes()
FAIL = "Unreviewed media detail historical source"
assert hashlib.sha256(RAW).hexdigest() == "a2209d2a371b0323480cadaa01d1726ac330c5fc6c3cc5473b13df8726fd79bd", FAIL
FIXTURE = json.loads(RAW)
GROUPS = [row for row in FIXTURE["historicalFragments"] if row["file"] == "static/portal/portal.js"]
assert FIXTURE["base"] == "051b936695638a5f083396194730861dc7831da1" and len(GROUPS) == 7, FAIL
assert len(FIXTURE["canonicalChanges"]) == 53, FAIL


def historical_media_detail_portal(source: str) -> str:
    assert isinstance(source, str), FAIL
    markers = ('audioWorkspaceText("pagination.audioFiles"', 'audioWorkspaceText("detail.tagsPlaceholder"',
               '}, "media-item-attach")')
    if not any(marker in source for marker in markers):
        return source
    previous = -1
    for group in GROUPS:
        owner, following = group["owner"], group["next"]
        assert source.count(owner) == source.count(following) == 1, FAIL + " unique owner"
        start, end = source.index(owner), source.index(following)
        assert previous < start < end, FAIL + " owner order"
        assert source[start:end] == group["new"], FAIL + " complete reviewed function"
        assert source.count(group["new"]) == 1, FAIL + " unique complete function"
        source = source[:start] + group["old"] + source[end:]
        previous = start
    assert not any(marker in source for marker in markers), FAIL + " detached marker"
    return source
