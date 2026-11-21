"""Finite historical-only media projection. Never current-renderer acceptance."""
from pathlib import Path
import hashlib
import json
import runpy

ROOT = Path(__file__).resolve().parents[2]
detail_inverse = runpy.run_path(str(ROOT / "tests/helpers/media_detail_historical_static.py"))["historical_media_detail_portal"]
RAW = (ROOT / "tests/fixtures/media-collection-locale-reviewed.json").read_bytes()
FAIL = "Unreviewed media collection historical source"
assert hashlib.sha256(RAW).hexdigest() == "f0da75ecb63d7f0abc432053441502cd8db99fcc487aa4b192a6514c84ea0515", FAIL
FIXTURE = json.loads(RAW)
assert FIXTURE["base"] == "4080b879ad8d6ded081aa47313bf9cac67121f0b", FAIL
GROUPS = [row for row in FIXTURE["historicalFragments"] if row["file"] == "static/portal/portal.js"]
assert len(GROUPS) == 5 and FIXTURE["task"] == "MEDIA-COLLECTION-LOCALE-20261120", FAIL


def historical_media_collection_portal(source: str) -> str:
    assert isinstance(source, str), FAIL
    source = detail_inverse(source)
    for group in GROUPS:
        owner, following = group["owner"], group["next"]
        if owner not in source and following not in source:
            continue
        assert source.count(owner) == source.count(following) == 1, FAIL + " owner count"
        start = source.index(owner)
        end = source.find(following, start)
        assert end > start, FAIL + " owner order"
        body = source[start:end]
        if body == group["old"]:
            continue
        assert body == group["new"], FAIL + " exact function"
        assert source.count(group["new"]) == 1, FAIL + " unique function"
        source = source[:start] + group["old"] + source[end:]
    return source
