"""Focused source-disposition checks for the Bot document-flow callbacks.

These tests deliberately exercise only the static auditor.  They never import
or start the Telegram Bot, a provider, a payment flow or a document runtime.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT_PATH = ROOT / "scripts" / "migration" / "audit_bot_to_web.py"
CONTRACT = (ROOT / "docs" / "migration" / "DOCFLOW_CALLBACK_CONTRACT.md").read_text(encoding="utf-8")
PARITY_GAP = json.loads((ROOT / "reports" / "migration" / "parity_gap.json").read_text(encoding="utf-8"))


def _audit_module():
    spec = importlib.util.spec_from_file_location("audit_bot_to_web_docflow", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_docflow_callback_dispositions_remain_non_runtime_source_evidence() -> None:
    audit = _audit_module()
    expected = {
        "docflow|send_more": "/document-workspace",
        "docflow|reset_files": "/document-workspace",
        "docflow|pop": "/document-workspace",
        "docflow|clear": "/document-workspace",
        "docflow|ask_pages": "/documents/split",
        "docflow|back": "/document-workspace",
        "docflow|compress|light": "/documents/compress",
        "docflow|compress|medium": "/documents/compress",
        "docflow|compress|strong": "/documents/compress",
        "docflow|confirm": "BOT_PENDING_CONFIRMATION_REQUIRED",
        "docflow|run": "BOT_PENDING_EXECUTION_REQUIRED",
    }
    mappings = {
        token: audit._map_callback(token, "callback_data", {"file": "bot.py", "line": 1}, {"/{page_path:path}"})
        for token in expected
    }
    assert {token: item["target"] for token, item in mappings.items()} == expected
    assert {item["status"] for item in mappings.values()} == {"NEEDS_FEATURE_DISPOSITION"}
    assert all("NO_RUNTIME_CLAIM" in item["source_dispositions"] for item in mappings.values())
    assert all("document_capability_key" not in item for item in mappings.values())
    assert "PROFILE_SEMANTICS_MISMATCH" in mappings["docflow|compress|light"]["source_dispositions"]
    assert "BOT_EXECUTION_DELIVERY_BOUNDARY" in mappings["docflow|run"]["source_dispositions"]

    # A family-wide fallback policy must not erase per-token evidence or turn
    # a precise source classification into coverage progress.
    before = dict(mappings["docflow|compress|strong"])
    audit._annotate_feature_disposition(mappings["docflow|compress|strong"])
    assert mappings["docflow|compress|strong"]["source_dispositions"] == before["source_dispositions"]
    assert mappings["docflow|compress|strong"]["source_evidence"] == before["source_evidence"]
    assert mappings["docflow|compress|strong"]["fallback_family"] == "docflow"


def test_docflow_contract_records_the_closed_navigation_boundary() -> None:
    for token in (
        "docflow|send_more",
        "docflow|reset_files",
        "docflow|pop",
        "docflow|clear",
        "docflow|ask_pages",
        "docflow|compress|light",
        "docflow|confirm",
        "docflow|run",
    ):
        assert token in CONTRACT
    for route in (
        "/documents/split",
        "/documents/merge",
        "/documents/compress",
        "/documents/image-to-pdf",
        "/documents/pdf-to-images",
        "/documents/pdf-to-word",
    ):
        assert route in CONTRACT
    for boundary in (
        "no query string",
        "Asset Vault UUID",
        "No Core Bridge request",
        "NO_RUNTIME_CLAIM",
    ):
        assert boundary in CONTRACT


def test_docflow_contract_count_matches_generated_callback_evidence() -> None:
    observed = [
        item
        for item in PARITY_GAP["callback_mappings"]
        if str(item.get("source") or "").casefold().startswith("docflow|")
    ]
    tokens = {str(item["source"]) for item in observed}
    assert len(observed) == 22
    assert len(tokens) == 10
    assert {str(item["status"]) for item in observed} == {"NEEDS_FEATURE_DISPOSITION"}
    assert all("COPIED_GUARDED" not in item.get("source_dispositions", []) for item in observed)
    assert "22 observed occurrences across\n10 concrete callback values" in CONTRACT
    for handler_only in ("docflow|pop", "docflow|back_received", "docflow|main"):
        assert handler_only in CONTRACT
