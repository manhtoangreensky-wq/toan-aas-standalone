"""Finite reviewed ARF source inputs only; current151 forward acceptance is separate."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
FAIL = "Unreviewed audio review historical source"
RAW = (ROOT / "tests/fixtures/audio-review-reviewed.json").read_bytes()
ROOT_RAW = (ROOT / "tests/fixtures/audio-review-contract.json").read_bytes()
assert hashlib.sha256(RAW).hexdigest() == "195a9af197e2a30c971eb9df061413368d42fd9af9139c3bb57d18195de9bb8d", FAIL
assert hashlib.sha256(ROOT_RAW).hexdigest() == "6528de3a693e4b89cf8e33c4f900723b4f02e506e78526012c808ece44f35163", FAIL
FIXTURE, CONTRACT = json.loads(RAW), json.loads(ROOT_RAW)
INTEGRATION = "static/portal/integration.js"
PORTAL = "static/portal/portal.js"
I18N = "static/portal/portal-i18n.js"
FILES = [INTEGRATION, PORTAL, I18N]
GROUPS = FIXTURE["historicalFragments"]
assert FIXTURE["schema"] == "AUDIO_REVIEW_REVIEWED_PROVENANCE_V1", FAIL
assert CONTRACT["schema"] == "AUDIO_REVIEW_EXPECTED_CONTRACT_V1", FAIL
assert FIXTURE["task"] == CONTRACT["task"] == "AUDIO-REVIEW-FEEDBACK-20261121", FAIL
assert FIXTURE["base"] == CONTRACT["base"] == "7cb8cb10486f5c175dca5db2c286a9f93a133c23", FAIL
assert FIXTURE["rootContractFile"] == "tests/fixtures/audio-review-contract.json", FAIL
assert FIXTURE["rootContractRawSha256"] == hashlib.sha256(ROOT_RAW).hexdigest(), FAIL
assert FIXTURE["allowedFiles"] == CONTRACT["allowedFiles"] == FILES, FAIL
assert FIXTURE["canonicalRecords"] == len(CONTRACT["canonicalChanges"]) == 11, FAIL
assert [sum(row["file"] == file for row in CONTRACT["canonicalChanges"]) for file in FILES] == [8, 2, 1], FAIL
assert len(GROUPS) == 5 and [row["file"] for row in GROUPS] == [
    INTEGRATION, INTEGRATION, INTEGRATION, PORTAL, I18N], FAIL
for group in GROUPS:
    assert all(isinstance(group[key], str) and group[key] for key in ["owner", "oldOwner", "next", "old", "new"]), FAIL
    assert hashlib.sha256(group["old"].encode()).hexdigest() == group["oldSha256"], FAIL
    assert hashlib.sha256(group["new"].encode()).hexdigest() == group["newSha256"], FAIL
assert len(FIXTURE["copyRows"]) == 31 and FIXTURE["copyRows"] == CONTRACT["copyRows"], FAIL
assert len({row["key"] for row in CONTRACT["copyRows"]}) == 31, FAIL
assert [(row["part"], row["records"]) for row in FIXTURE["workers"]] == [
    ("feedback", 8), ("renderer", 2), ("catalogue", 1)], FAIL
assert all(row["codeFailures"] == 0 and row["fullMapExact"] is True and row["publicSourcesExact"] == 4
           and re.fullmatch(r"[a-f0-9]{64}", row["proposalRawSha256"])
           and re.fullmatch(r"[a-f0-9]{64}", row["packetRawSha256"]) for row in FIXTURE["workers"]), FAIL
assert len(FIXTURE["applicationBaseline"]) == len({row["file"] for row in FIXTURE["applicationBaseline"]}) == 151, FAIL
RENDERER_SIGNALS = [f'audioWorkspaceText("{row["short"]}", "{row["vi"]}"' for row in CONTRACT["staticRows"]]


def _owned(source: str, file: str) -> bool:
    if file == INTEGRATION:
        return bool(re.search(r'\baudioHubReviewFeedbackText\b|audioWorkspace\.feedback\.review\.|'
                              r'mediaWorkspaceFeedbackText\("review\.', source))
    if file == PORTAL:
        return bool(re.search(r"\baudioHubReviewSourceText\b", source)
                    or any(marker in source for marker in RENDERER_SIGNALS))
    return bool(re.search(r"\bAUDIO_REVIEW_CUSTOMER_COPY\b|audioWorkspace\.feedback\.review\.|"
                          r"audioWorkspace\.review\.result\.", source))


def _boundary(source: str, marker: str) -> int:
    assert source.count(marker) == 1, FAIL + " unique boundary " + marker
    return source.index(marker)


def _ordered(*positions: int) -> None:
    assert all(value >= 0 and (not index or value > positions[index - 1])
               for index, value in enumerate(positions)), FAIL + " structural owner order"


def historical_audio_review_source(source: str, file: str) -> str:
    """Restore only five exact reviewed regions, preserving all outside bytes."""
    assert isinstance(source, str), FAIL + " source type"
    assert isinstance(file, str), FAIL + " file type"
    if file not in FILES or not _owned(source, file):
        return source
    groups = [row for row in GROUPS if row["file"] == file]
    points = []
    for group in groups:
        start, end = _boundary(source, group["owner"]), _boundary(source, group["next"])
        assert end > start, FAIL + " bounded owner order"
        assert source[start:end] == group["new"], FAIL + " complete bounded region"
        assert source.count(group["new"]) == 1, FAIL + " unique current region"
        points.append(start)
    if file == INTEGRATION:
        constants = _boundary(source, "  const AUDIO_HUB_REVIEW_PACK_CHECK_KEYS = ")
        action = _boundary(source, "  async function handleAction(event) {")
        action_end = _boundary(source, "  function synchronizeScriptToScreenEpisodeFields(target) {")
        _ordered(constants, points[0], action, points[1], points[2], action_end)
    elif file == PORTAL:
        _ordered(_boundary(source, "  function mediaAudioOperationHandoffAsset(item, collection) {"),
                 points[0], _boundary(source, groups[0]["next"]))
        _boundary(source, groups[0]["oldOwner"])
    else:
        verify = _boundary(source, "  function verifyEqualKeysets() {")
        call = _boundary(source, "  verifyEqualKeysets();")
        freeze_function = _boundary(source, "  function deepFreeze(value) {")
        freeze_call = _boundary(source, "  deepFreeze(MESSAGES);")
        _ordered(verify, points[0], call, freeze_function, freeze_call)
        assert source[points[0] + len(groups[0]["new"]):].startswith(groups[0]["next"]), FAIL + " immediate catalogue boundary"
    for group in reversed(groups):
        source = source.replace(group["new"], group["old"], 1)
    assert not _owned(source, file), FAIL + " partial or detached owned marker"
    return source
