"""Finite pending-feedback projection for earlier historical tests only."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
RAW = (ROOT / "tests/fixtures/audio-review-pending-contract.json").read_bytes()
FAIL = "Unreviewed audio review pending feedback"
NORMALIZED = RAW.replace(b"\r\n", b"\n")
assert hashlib.sha256(NORMALIZED).hexdigest() == "5f9c628132c86d4b7b5fa106cfa16b68a015b15a1bffa49dd303c4192db42aac", FAIL
assert RAW in (NORMALIZED, NORMALIZED.replace(b"\n", b"\r\n")), FAIL + " uniform checkout newlines"
CONTRACT = json.loads(NORMALIZED)
INTEGRATION, CATALOGUE = "static/portal/integration.js", "static/portal/portal-i18n.js"
assert CONTRACT["base"] == "cd9c5c14263e1397531056e318a9f46394a8562d", FAIL
assert [row["file"] for row in CONTRACT["records"]] == [INTEGRATION, INTEGRATION, CATALOGUE], FAIL
MARKERS = {
    INTEGRATION: ('"review.notFound"', '"review.conflict"', '"review.maintenance"',
                  "} catch (error) {\n          if (!audioHubReviewPackRequestIsCurrent(requestEpoch, sessionEpoch, route, collectionId, expectedRevision)) return;"),
    CATALOGUE: ('"audioWorkspace.feedback.review.notFound"', '"audioWorkspace.feedback.review.conflict"',
                '"audioWorkspace.feedback.review.maintenance"'),
}


def _boundary(source: str, part: str) -> int:
    assert source.count(part) == 1, FAIL + " unique boundary"
    return source.index(part)


def historical_audio_review_pending_source(source: str, file: str) -> str:
    """Restore exact records; current candidate acceptance remains forward-only."""
    assert isinstance(source, str) and isinstance(file, str), FAIL
    if file not in MARKERS or not any(marker in source for marker in MARKERS[file]):
        return source
    records = [row for row in CONTRACT["records"] if row["file"] == file]
    for row in records:
        assert source.count(row["new"]) == 1, FAIL + " exact current record"
    if file == INTEGRATION:
        action = _boundary(source, '      if (action === "audio-hub-review-pack-compose") {')
        following = _boundary(source, '      if (action === "media-collection-compose") {')
        catch_at = source.index(records[0]["new"])
        helper = _boundary(source, "  function audioHubReviewFeedbackText(")
        next_helper = _boundary(source, "  function audioHubReviewPackBoundaryIsSafe(")
        mapping_at = source.index(records[1]["new"])
        assert action < catch_at < following and helper < mapping_at < next_helper, FAIL + " ownership"
    else:
        verify = _boundary(source, "  function verifyEqualKeysets() {")
        at = source.index(records[0]["new"])
        call = _boundary(source, "  verifyEqualKeysets();")
        freeze = _boundary(source, "  deepFreeze(MESSAGES);")
        assert verify < at < call < freeze, FAIL + " catalogue ownership"
    for row in reversed(records):
        source = source.replace(row["new"], row["old"], 1)
    assert not any(marker in source for marker in MARKERS[file]), FAIL + " detached marker"
    return source
