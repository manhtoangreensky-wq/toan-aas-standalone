"""Focused machine-testable truth contracts for Program P0.WEB.ERP.PRODUCTION_COMPLETION (SPEC-00)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INVENTORY_PATH = REPO_ROOT / "reports" / "audit" / "P0-SPEC00-TRUTH-CONTRACT-INVENTORY.json"
CHECKLIST_PATH = REPO_ROOT / "reports" / "audit" / "P0-WEB-ERP-MASTER-CHECKLIST.md"


@pytest.fixture(scope="module")
def inventory() -> dict:
    assert INVENTORY_PATH.exists(), f"Contract inventory missing at {INVENTORY_PATH}"
    with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_spec00_reporting_truth_invariants(inventory: dict) -> None:
    """Reporting truth must reflect realistic partial states, preventing false-green declarations."""
    truth = inventory["reporting_truth"]

    assert truth["FULL_WEB_APP_LIVE"] == "NO", "Full Web App cannot be claimed live while domains are partial"
    assert truth["MONITORING_LIVE"] == "PARTIAL", "Monitoring is partial until Autopilot telemetry is proven"
    assert truth["FINANCE_LIVE"] == "PARTIAL", "Finance is partial until Bot Core ledger aggregation is proven"
    assert truth["ADMIN_WRITE_LIVE"] == "PARTIAL", "Admin write is partial until all write boundaries are verified"
    assert truth["DATA_TRUTH_STATUS"] == "PARTIAL", "Data truth is partial due to hardcoded planning/growth pages"

    assert truth["ZERO_IS_NOT_UNKNOWN"] is True
    assert truth["HTTP200_IS_NOT_BUSINESS_SUCCESS"] is True
    assert truth["WALLET_DIRECT_MUTATIONS_PERMITTED"] is False
    assert truth["OWNER_SAFETY_GATES_ACTIVE"] >= 8


def test_spec00_inventory_counts_and_distribution(inventory: dict) -> None:
    """Audit must encompass all 54 discrete business functions across 9 domains."""
    counts = inventory["counts"]
    functions = inventory["functions"]

    assert len(functions) == 54
    assert counts["total_functions"] == 54
    assert counts["working"] == 29
    assert counts["partial"] == 14
    assert counts["empty_valid"] == 2
    assert counts["placeholder"] == 4
    assert counts["read_only"] == 5
    assert counts["hardcoded_metric_pages"] == 3

    valid_domains = {
        "AUTH_ACCOUNT",
        "CUSTOMER_CRM_SUPPORT",
        "OPERATIONS_JOBS",
        "RELIABILITY_MONITORING",
        "FINANCE_PAYMENT",
        "PRODUCT_COMMERCE",
        "CONTENT_GROWTH",
        "ADMINISTRATION_SECURITY_AUDIT",
        "GOVERNANCE_DOCUMENTS_LEGAL",
    }
    actual_domains = {fn["domain"] for fn in functions}
    assert actual_domains == valid_domains


def test_spec00_working_status_rigor(inventory: dict) -> None:
    """No function may receive WORKING unless implemented, unit tested, and real data proven."""
    for fn in inventory["functions"]:
        fn_id = fn["function_id"]
        status = fn["status"]

        if status == "WORKING":
            assert fn["implemented"] is True, f"{fn_id} is marked WORKING but implemented is False"
            assert fn["unit_tested"] is True, f"{fn_id} is marked WORKING but unit_tested is False"
            assert fn["real_data_proven"] is True, f"{fn_id} is marked WORKING but real_data_proven is False"
            assert fn["production_proven"] is True, f"{fn_id} is marked WORKING but production_proven is False"

            # If write action, must have write proven
            if "POST" in fn["api_endpoint"] or "PUT" in fn["api_endpoint"]:
                if fn_id in {"FN-01", "FN-02", "FN-03", "FN-04", "FN-08", "FN-10", "FN-11", "FN-24", "FN-25", "FN-27"}:
                    assert fn["write_proven"] is True, f"{fn_id} is a WORKING write action but write_proven is False"


def test_spec00_reliability_http200_is_not_working(inventory: dict) -> None:
    """FN-20 (Reliability summary) must be PARTIAL despite clean HTTP 200 envelope."""
    fn20 = next(fn for fn in inventory["functions"] if fn["function_id"] == "FN-20")
    assert fn20["status"] == "PARTIAL"
    assert fn20["real_data_proven"] is False


def test_spec00_hardcoded_metric_pages_are_not_working(inventory: dict) -> None:
    """Planning, Growth, and Trends pages must not be marked WORKING."""
    hardcoded_ids = {"FN-31", "FN-40", "FN-42"}
    for fn in inventory["functions"]:
        if fn["function_id"] in hardcoded_ids:
            assert fn["status"] in {"PLACEHOLDER", "PARTIAL"}, f"{fn['function_id']} must not be marked WORKING"
            assert fn["real_data_proven"] is False


def test_spec00_wallet_zero_mutation_safety_invariant(inventory: dict) -> None:
    """Wallet balance reading (FN-23) must have write_proven False, guaranteeing Gate 4."""
    fn23 = next(fn for fn in inventory["functions"] if fn["function_id"] == "FN-23")
    assert fn23["write_proven"] is False
    assert fn23["status"] == "WORKING"
    assert "READ-ONLY" in fn23["notes"]


def test_spec00_master_checklist_completeness() -> None:
    """Master checklist must track all 19 SPECs (SPEC-00 to SPEC-18) and all 8 Owner gates."""
    assert CHECKLIST_PATH.exists(), f"Master checklist missing at {CHECKLIST_PATH}"
    content = CHECKLIST_PATH.read_text(encoding="utf-8")

    # Verify all 19 SPECs
    for i in range(19):
        spec_id = f"SPEC-{i:02d}"
        assert spec_id in content, f"Missing {spec_id} in master checklist"

    # Verify all 8 Owner gates
    for g in ["GATE-A", "GATE-B", "GATE-C", "GATE-D", "GATE-E", "GATE-F", "GATE-G", "GATE-H"]:
        assert g in content, f"Missing {g} in master checklist"
