"""Finite native Gallery source inverse for historical QA, never app runtime."""

import hashlib
import json
from pathlib import Path
import re
from tests.helpers.document_natural_copy_historical import document_natural_historical_source

from tests.helpers.gallery_native_transport_historical import (
    gallery_native_transport_historical_source,
)
from tests.helpers.admin_guard_customer_copy_historical import (
    admin_guard_customer_copy_historical_source,
)


_FAIL = "Unreviewed Gallery native history"
_BASE = "29e0c154dfd247ac4b0a68cd6336ec83fb3af8ef"
_PORTAL = "static/portal/portal.js"
_I18N = "static/portal/portal-i18n.js"
_BACKEND_FILES = {"copyfast_free_prompt_gallery.py", "copyfast_memory.py"}
_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(f"{_FAIL}: {detail}")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fixture(name: str, pin: str, count: int) -> dict:
    raw = (_FIXTURES / name).read_bytes().decode("utf-8").replace("\r\n", "\n")
    _require(_hash(raw) == pin, f"{name} fixture hash")
    data = json.loads(raw)
    _require(data["base_sha"] == _BASE and len(data["records"]) == count, f"{name} BASE/count")
    for row in data["records"]:
        _require(isinstance(row["before"], str) and isinstance(row["after"], str), "record shape")
        _require(_hash(row["after"]) == row["after_lf_sha256"], "after hash")
        if "before_lf_sha256" in row:
            _require(_hash(row["before"]) == row["before_lf_sha256"], "before hash")
    return data


_UI = _fixture("gallery-native-history.json", "4b035b41da5204033d8fd6af9a77d64c74523bba33d71ddbd4427f9a9e236435", 5)
_TRANSPORT = _fixture("gallery-native-transport-history.json", "70194054446d00266cd8d0c692d668588a29d4dcb23cdbf647e7c74cfd141d05", 11)
_BACKEND = _fixture("gallery-native-backend-history.json", "d6fedb7c38b7abec4cd138069dc5aa2634945aff7003b1b0039407c66fa5733f", 7)
_require(all(row["file"] in {_PORTAL, _I18N} for row in _UI["records"]), "UI target")
_require(_TRANSPORT["file"] == "static/portal/integration.js", "transport target")
_require(_BACKEND["conversation_id"] == "bffacabe-abf0-40df-92c2-bdf9a9b6f0b3", "backend conversation")
_require(all(row["file"] in _BACKEND_FILES and row["proposal_record"] == index
             for index, row in enumerate(_BACKEND["records"])), "backend targets/order")
_KEYS = [key for key, _ in _UI["snapshots"]["vi"]]
_require(len(_KEYS) == len(set(_KEYS)) == 40, "forty unique keys")
for _locale in ("vi", "en", "zh"):
    _require([key for key, _ in _UI["snapshots"][_locale]] == _KEYS, "locale key order")
_DECLARATIONS = re.compile(r'"(' + "|".join(re.escape(key) for key in _KEYS) + r')"\s*:')
_PYTHON_DECLARATION = re.compile(r"^(?:async )?def [A-Za-z_][A-Za-z0-9_]*\(", re.MULTILINE)
_TOP_LEVEL_PYTHON = re.compile(r"^(?:(?:async )?def |class |@)", re.MULTILINE)
_BACKEND_SIGNALS = re.compile(
    r"^from copyfast_gallery_locale import |gallery_locale_text\(|localized_gallery_item\("
    r"|gallery_taxonomy_label\(|^def _matches_native_taxonomy\("
    r'|lang: str \| None = Query\(None, pattern="\^\(vi\|en\|zh\)\$"\)', re.MULTILINE,
)
_PORTAL_SIGNALS = re.compile(
    r'freePromptGalleryTaxonomyLabel\s*\(|freePromptGalleryText\("feedback\.loading"'
    r'|context\.freePromptGalleryReadState\s*===\s*"loading"'
)


def _once(source: str, part: str, label: str) -> int:
    _require(isinstance(part, str) and bool(part) and source.count(part) == 1, f"unique {label}")
    return source.index(part)


def _end(source: str, start: int, closing: str, label: str) -> int:
    at = source.find(closing, start)
    _require(at > start, f"closed {label}")
    return at + len(closing)


def _line_start(source: str, index: int) -> bool:
    return index == 0 or source[index - 1] == "\n"


def _backend_slot(source: str, row: dict) -> None:
    start = _once(source, row["after"], "approved backend after")
    stop = start + len(row["after"])
    slot = row["slot"]
    previous = _once(source, slot["previous"], "previous backend owner")
    _require(_line_start(source, start) and _line_start(source, previous), "backend top-level placement")
    lower = previous + len(slot["previous"])
    if slot["kind"] == "import":
        owner = _once(source, slot["owner"], "locale import owner")
        _require(_line_start(source, owner) and start <= owner < stop, "top-level owned import")
    else:
        _require(slot["kind"] in {"function", "partial_function", "final_function"}, "known backend slot")
        lower = _end(source, previous, slot["previous_end"], "previous backend body")
        owner = _once(source, slot["owner"], "backend declaration owner")
        _require(start <= owner < stop and _line_start(source, owner), "backend owner inside record")
        for marker in _PYTHON_DECLARATION.findall(row["after"]):
            _once(source, marker, "Python declaration owner")
        _require(not _TOP_LEVEL_PYTHON.search(source[lower:start]), "no foreign owner in backend slot")
    _require(lower <= start, "backend previous boundary")
    if slot["kind"] == "partial_function":
        remaining = source[stop:]
        match = _TOP_LEVEL_PYTHON.search(remaining)
        next_owner = match.start() if match else len(remaining)
        following = remaining.find(slot["following"])
        _require(0 <= following < next_owner, "backend same-function following boundary")
        _require(remaining[:next_owner].count(slot["following"]) == 1, "unique local following")
    elif slot["following"] is not None:
        _require(stop <= _once(source, slot["following"], "following backend owner"), "backend following boundary")


def _function_slot(source: str, row: dict, previous: str, following: str) -> None:
    start = _once(source, row["after"], row["owner"])
    previous_start = _once(source, f"  function {previous}(", "previous UI owner")
    previous_end = source.find("\n  }\n", previous_start)
    following_start = _once(source, following, "following UI owner")
    _require(previous_end > previous_start and start >= previous_end + 5
             and start + len(row["after"]) <= following_start, "UI function slot")


def _ui_inverse(source: str, file: str) -> str:
    rows = [row for row in _UI["records"] if row["file"] == file]
    if file == _PORTAL:
        if not _PORTAL_SIGNALS.search(source):
            return source
        prior = -1
        for row in rows:
            start = _once(source, row["after"], row["owner"])
            _require(start > prior, "UI source order")
            prior = start
        for owner in ("freePromptGalleryTaxonomyLabel", "freePromptGalleryFilterFields",
                      "freePromptGalleryTags", "renderFreePromptGallery"):
            _once(source, f"  function {owner}(", "UI declaration owner")
        _function_slot(source, rows[0], "freePromptGalleryListingState", "  function freePromptGalleryTags(")
        _function_slot(source, rows[1], "freePromptGalleryFilterFields", "  function renderFreePromptGalleryCards(")
        _function_slot(source, rows[2], "renderFreePromptGallerySaveResult", "  const VIETQR_BANKS = [")
    else:
        found = _DECLARATIONS.findall(source)
        if not found:
            return source
        for key in _KEYS:
            _require(found.count(key) == 3, "i18n declaration ownership")
        combined = rows[0]["after"].replace(rows[1]["before"], rows[1]["after"], 1)
        start = _once(source, combined, "complete ordered i18n blocks")
        _once(source, "  verifyEqualKeysets();", "verification anchor")
        previous = '  MESSAGES.zh["portal.form.requiredWarning"] = "请先填写必填项，然后继续。";'
        previous_start = _once(source, previous, "prior i18n slot")
        next_start = _once(source, "  function deepFreeze(value) {", "following i18n slot")
        _require(start >= previous_start + len(previous) and start + len(combined) <= next_start, "i18n slot")
    for row in reversed(rows):
        _once(source, row["after"], "reverse exact UI record")
        source = source.replace(row["after"], row["before"], 1)
    return source


def gallery_native_historical_source(source: str, file: str) -> str:
    """Reverse only the five UI, eleven transport, or seven backend records."""
    _require(isinstance(source, str), "string source")
    source = document_natural_historical_source(source, file)
    source = admin_guard_customer_copy_historical_source(source, file)
    source = gallery_native_transport_historical_source(source, file)
    if file in _BACKEND_FILES and _BACKEND_SIGNALS.search(source):
        for row in reversed([row for row in _BACKEND["records"] if row["file"] == file]):
            _backend_slot(source, row)
            source = source.replace(row["after"], row["before"], 1)
    return _ui_inverse(source, file) if file in {_PORTAL, _I18N} else source
