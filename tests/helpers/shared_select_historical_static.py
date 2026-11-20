"""Finite historical input projection; never used by the current renderer."""
from pathlib import Path
import hashlib
import json
import re
import runpy

ROOT = Path(__file__).resolve().parents[2]
media_inverse = runpy.run_path(str(ROOT / "tests/helpers/media_collection_historical_static.py"))["historical_media_collection_portal"]
RAW = (ROOT / "tests/fixtures/shared-select-labels-reviewed.json").read_bytes()
FAIL = "Unreviewed Shared select historical source"
assert hashlib.sha256(RAW).hexdigest() == "7cb67db3464cb45d3e0b243f388affb981fd4f5780e0ebb28105865885786817", FAIL
FIXTURE = json.loads(RAW)
assert FIXTURE["base"] == "46423a6df9af67ac7ccabd88686d4cb42523a078", FAIL
EDITS = [row for row in FIXTURE["canonicalChanges"] if row["file"] == "static/portal/portal.js"]
KEYS = [row[0] for row in FIXTURE["rows"]]
assert len(EDITS) == 3 and len(KEYS) == 4 and all(row["count"] == 1 for row in EDITS), FAIL
OWNER = "  function renderFields(fields, enabled, context, fieldValues, idNamespace) {"
NEXT = "  function statusMessage(page, status, context) {"
LOOKUP = re.compile(r"""\b(?:[A-Za-z_$][\w$]*\.)*(?:uiText|t)\(\s*["'](sharedSelect[^"']*)["']""")


def historical_shared_select_portal(source: str) -> str:
    assert isinstance(source, str), FAIL
    source = media_inverse(source)
    title_raw = (ROOT / "tests/fixtures/shared-select-reminder-title-reviewed.json").read_bytes()
    assert hashlib.sha256(title_raw).hexdigest() == "66d8d0d6bdf45c9bb59c8c3e3095bb67f1de44933ef73c260a31094045840132", FAIL
    title_edit = json.loads(title_raw)["canonicalChanges"][0]
    title_owner, title_next = "  function localizedPageTitle(page, context) {", "  function documentTitle(page, context) {"
    if title_edit["new"] in source:
        assert source.count(title_edit["new"]) == source.count(title_owner) == source.count(title_next) == 1, FAIL + " title count"
        assert source.index(title_edit["new"]) == source.index(title_owner) < source.index(title_next), FAIL + " title placement"
        source = source.replace(title_edit["new"], title_edit["old"], 1)
    elif title_owner in source:
        title_body = source[source.index(title_owner):source.index(title_next)]
        assert '"/reminders"' not in title_body, FAIL + " title changed phase"
    lookups = LOOKUP.findall(source)
    unknown = re.findall(r"\bsharedSelect[A-Za-z0-9_]*\s*\(", source)
    declarations = re.findall(r"""(?:["']sharedSelect[^"']*["']|\bsharedSelect[A-Za-z0-9_.]*)\s*:""", source)
    accessors = re.findall(r"""\[\s*["']sharedSelect[^"']*["']\s*\]""", source)
    if not lookups and not unknown and not declarations and not accessors:
        return source
    assert not unknown and not declarations and not accessors, FAIL + " unknown owned syntax"
    assert lookups == [KEYS[2], KEYS[3], KEYS[0], KEYS[1]], FAIL + " lookup set"
    assert source.count(OWNER) == source.count(NEXT) == 1, FAIL + " owner count"
    start, end = source.index(OWNER), source.index(NEXT)
    assert end > start and source[start:end].endswith('    }).join("")}</div>`;\n  }\n\n'), FAIL + " owner bounds"
    for edit in EDITS:
        assert source.count(edit["new"]) == 1 and source.count(edit["old"]) == 0, FAIL + " partial/mixed/duplicate"
        point = source.index(edit["new"])
        assert start < point and point + len(edit["new"]) < end, FAIL + " displaced"
    for edit in reversed(EDITS):
        source = source.replace(edit["new"], edit["old"], 1)
    return source
