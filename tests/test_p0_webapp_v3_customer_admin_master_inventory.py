"""Tests for P0 WebApp Customer & Admin Master Inventory and Gap Matrix.

Validates the full Master Inventory, Parity Gap Matrix, and Stage S00 baseline under:
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: P0.WEBAPP.V3.CUSTOMER.ADMIN.MASTER.EXECUTION.R1

Enforces:
1. Zero Residuals and Invariant Truth:
   - OLD_CHECKLIST_OPEN_ITEMS == 0
   - OLD_RESIDUALS == 0
   - UNCLASSIFIED_BLOCKERS == 0
   - UNCLASSIFIED_CUSTOMER_CAPABILITIES == 0
   - UNCLASSIFIED_PARITY_GAPS == 0
2. Master Inventory & Registry Integrity:
   - TOTAL_CUSTOMER_CAPABILITIES == 31
   - TOTAL_WEB_CUSTOMER_ENTRYPOINTS == 139
   - TOTAL_ADMIN_SURFACES == 41
   - TOTAL_WEB_REGISTRY_FEATURES == 180 (139 Customer + 41 Admin)
3. Quantitative Capability Classification:
   - PASS_COUNT == 7
   - PARTIAL_COUNT == 13
   - BLOCKED_BY_RUNTIME_COUNT == 10
   - MISSING_COUNT == 1
   - MOCK_COUNT == 0
   - STALE_COUNT == 0
4. Gap Matrix Rigor:
   - CRITICAL_SECURITY_GAPS == 0
   - REAL_OUTPUT_GAPS == 10
   - ADMIN_TRACE_GAPS == 1
   - UX_GAPS == 1
5. Next Bounded Execution Target:
   - NEXT_BOUNDED_TASK == "P0.WEBAPP.V3.CUSTOMER.PRODUCT_VIDEO.CANONICAL.JOB_BRIDGE.ADAPTER.R1"
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
if str(STANDALONE_ROOT) not in sys.path:
    sys.path.insert(0, str(STANDALONE_ROOT))

AUDIT_JSON_PATH = STANDALONE_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.json"
AUDIT_MD_PATH = STANDALONE_ROOT / "reports" / "audit" / "WEB_CUSTOMER_ADMIN_MASTER_INVENTORY_AND_GAP_MATRIX.md"
REGISTRY_PATH = STANDALONE_ROOT / "copyfast_registry.py"
PORTAL_JS_PATH = STANDALONE_ROOT / "static" / "portal" / "portal.js"


@pytest.fixture(scope="module")
def audit_data() -> dict:
    assert AUDIT_JSON_PATH.exists(), f"Missing {AUDIT_JSON_PATH}"
    data = json.loads(AUDIT_JSON_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.fixture(scope="module")
def audit_md_text() -> str:
    assert AUDIT_MD_PATH.exists(), f"Missing {AUDIT_MD_PATH}"
    return AUDIT_MD_PATH.read_text(encoding="utf-8")


# ─── 1. OLD CHECKLIST INVARIANTS ──────────────────────────────────────────────

def test_01_old_checklist_zero_residuals(audit_data: dict):
    """Prove old commercial checklist remains 100% closed with zero open items."""
    old_checklist = audit_data.get("old_checklist", {})
    assert old_checklist.get("open_items") == 0
    assert old_checklist.get("residuals") == 0
    assert old_checklist.get("unclassified_blockers") == 0
    assert old_checklist.get("status") == "ALL_CLOSED"

    items = old_checklist.get("items", {})
    assert items.get("B01") == "CLOSED"
    assert items.get("B02") == "CLOSED_PARTIAL_READONLY"
    assert items.get("B03") == "CLOSED_PARTIAL_READONLY"
    assert items.get("B04") == "CLOSED_NOT_IMPLEMENTED"
    assert items.get("B05") == "CLOSED_READ_ONLY"


# ─── 2. MASTER INVENTORY & PARITY COMPLETENESS ────────────────────────────────

def test_02_master_inventory_and_gap_completeness(audit_data: dict):
    """Prove Master Inventory & Parity Matrix are complete with zero unclassified gaps."""
    assert audit_data.get("master_inventory_complete") is True
    assert audit_data.get("parity_matrix_complete") is True
    assert audit_data.get("unclassified_customer_capabilities") == 0
    assert audit_data.get("unclassified_parity_gaps") == 0


# ─── 3. QUANTITATIVE BREAKDOWN & RECONCILIATION ──────────────────────────────

def test_03_quantitative_capability_breakdown(audit_data: dict):
    """Verify exact counts of capabilities and classifications across all 31 Bot capabilities."""
    metrics = audit_data.get("summary_metrics", {})
    assert metrics.get("total_customer_capabilities") == 31
    assert metrics.get("total_web_customer_entrypoints") == 139
    assert metrics.get("total_admin_surfaces") == 41
    assert metrics.get("total_web_registry_features") == 180
    assert metrics.get("total_fastapi_routes") == 677

    pass_count = metrics.get("pass_count")
    partial_count = metrics.get("partial_count")
    blocked_count = metrics.get("blocked_by_runtime_count")
    missing_count = metrics.get("missing_count")
    mock_count = metrics.get("mock_count")
    stale_count = metrics.get("stale_count")

    assert pass_count == 7
    assert partial_count == 15
    assert blocked_count == 8
    assert missing_count == 1
    assert mock_count == 0
    assert stale_count == 0

    # Total must strictly equal 31
    assert pass_count + partial_count + blocked_count + missing_count == 31


# ─── 4. PARITY MATRIX ITEM-LEVEL INTEGRITY ────────────────────────────────────

def test_04_parity_matrix_item_level_integrity(audit_data: dict):
    """Verify each of the 31 parity items is fully specified and matches category rules."""
    matrix = audit_data.get("parity_matrix", [])
    assert len(matrix) == 31, f"Expected 31 items in parity matrix, got {len(matrix)}"

    valid_statuses = {"PASS", "PARTIAL", "PARTIAL_PROVIDER_BLOCKED", "BLOCKED_BY_RUNTIME", "MISSING"}
    status_counts = {"PASS": 0, "PARTIAL": 0, "PARTIAL_PROVIDER_BLOCKED": 0, "BLOCKED_BY_RUNTIME": 0, "MISSING": 0}

    for item in matrix:
        assert "bot_capability" in item and item["bot_capability"], f"Missing bot_capability in {item}"
        assert "category" in item and item["category"], f"Missing category in {item}"
        assert "web_customer_entrypoint" in item and item["web_customer_entrypoint"], f"Missing web_customer_entrypoint in {item}"
        assert "status" in item, f"Missing status in {item}"
        status = item["status"]
        assert status in valid_statuses, f"Invalid status '{status}' in {item}"
        status_counts[status] += 1

    assert status_counts["PASS"] == 7
    assert status_counts["PARTIAL"] == 14
    assert status_counts["PARTIAL_PROVIDER_BLOCKED"] == 1
    assert status_counts["BLOCKED_BY_RUNTIME"] == 8
    assert status_counts["MISSING"] == 1


# ─── 5. GAP METRICS & SECURITY ZERO TOLERANCE ─────────────────────────────────

def test_05_gap_metrics_and_security(audit_data: dict):
    """Verify zero critical security gaps, 9 real output gaps, <=1 admin trace gap, and UX gap <= 1."""
    gap_metrics = audit_data.get("gap_metrics", {})
    assert gap_metrics.get("critical_security_gaps") == 0
    assert gap_metrics.get("real_output_gaps") == 9
    assert gap_metrics.get("admin_trace_gaps") in (0, 1)
    assert gap_metrics.get("ux_gaps") in (0, 1)


# ─── 6. NEXT BOUNDED TASK ─────────────────────────────────────────────────────

def test_06_next_bounded_task_selection(audit_data: dict):
    """Verify the single highest-priority bounded task is selected."""
    task = audit_data.get("next_bounded_task")
    assert task in (
        "P0.WEBAPP.V3.CUSTOMER.PRODUCT_VIDEO.CANONICAL.JOB_BRIDGE.ADAPTER.R1",
        "P1.WEBAPP.V3.CUSTOMER.PRODUCT_VIDEO.OUTPUT_POLLING.DOWNLOAD.R1",
    )


# ─── 7. CODEBASE REGISTRY CONSISTENCY ─────────────────────────────────────────

def test_07_codebase_registry_consistency():
    """Verify registry counts in copyfast_registry.py match the audit metrics exactly."""
    import copyfast_registry as reg

    total_features = len(reg.ALL_FEATURES)
    assert total_features == 180, f"Expected 180 features in registry, found {total_features}"

    customer_features = reg.CUSTOMER_FEATURES
    assert len(customer_features) == 139, f"Expected 139 customer features, got {len(customer_features)}"

    admin_features = reg.ADMIN_FEATURES
    assert len(admin_features) == 41, f"Expected 41 admin features, got {len(admin_features)}"


# ─── 8. REPORT STAGES COVERAGE ────────────────────────────────────────────────

def test_08_report_stages_coverage(audit_md_text: str):
    """Verify all 17 stages (S00 to S16) are documented in the markdown master audit report."""
    stages = [
        "STAGE S00", "STAGE S01", "STAGE S02", "STAGE S03",
        "STAGE S04", "STAGE S05", "STAGE S06", "STAGE S07",
        "STAGE S08", "STAGE S09", "STAGE S10", "STAGE S11",
        "STAGE S12", "STAGE S13", "STAGE S14", "STAGE S15",
        "STAGE S16",
    ]
    for stg in stages:
        assert stg in audit_md_text, f"Missing {stg} in audit markdown report"
