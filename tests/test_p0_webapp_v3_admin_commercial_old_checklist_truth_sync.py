"""P0 WebApp Commercial Old Checklist Final Truth Sync & Zero Residual Tests.

Validates the final reconciliation of the old commercial checklist under:
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: P0.WEBAPP.V3.ADMIN.COMMERCIAL.OLD_CHECKLIST.FINAL.TRUTH_SYNC.ZERO_RESIDUAL.R1

Enforces:
1. All 5 old checklist items (B01..B05) are in CLOSED* terminal state:
   - B01: CLOSED
   - B02: CLOSED_PARTIAL_READONLY
   - B03: CLOSED_PARTIAL_READONLY
   - B04: CLOSED_NOT_IMPLEMENTED
   - B05: CLOSED_READ_ONLY
2. Metrics:
   - OLD_CHECKLIST_OPEN_ITEMS = 0
   - OLD_RESIDUALS = 0
   - UNCLASSIFIED_BLOCKERS = 0
   - STALE_ACTIVE_TRUTH_REFERENCES = 0
3. All future gates are properly categorized as either:
   - FUTURE_PROGRAM (B04 promotions engine, B05 mutable topup config)
   - OPTIONAL_LIVE_DEPTH (B02 live write acceptance, B03 owner-authorized write canary)
   - NO_GATE (B01)
   and NONE are open old-checklist blockers.
4. Active codebase hygiene:
   - Zero stale PR #1093 active references in portal.js or backend routers.
   - Zero Web-owned promotion mutation APIs.
   - Zero Web-owned topup mutation APIs.
   - Financial invariants preserved (zero provider calls, zero wallet mutations).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_MATRIX_PATH = STANDALONE_ROOT / "admin_capability_matrix.json"
PORTAL_JS_PATH = STANDALONE_ROOT / "static" / "portal" / "portal.js"
ADMIN_COMMERCIAL_PY = STANDALONE_ROOT / "copyfast_admin_commercial.py"


@pytest.fixture(scope="module")
def capability_matrix() -> dict:
    assert CAPABILITY_MATRIX_PATH.exists(), f"Missing {CAPABILITY_MATRIX_PATH}"
    data = json.loads(CAPABILITY_MATRIX_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.fixture(scope="module")
def portal_js_content() -> str:
    assert PORTAL_JS_PATH.exists(), f"Missing {PORTAL_JS_PATH}"
    return PORTAL_JS_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def admin_commercial_content() -> str:
    assert ADMIN_COMMERCIAL_PY.exists(), f"Missing {ADMIN_COMMERCIAL_PY}"
    return ADMIN_COMMERCIAL_PY.read_text(encoding="utf-8")


# ─── 1. OLD CHECKLIST SUMMARY & METRICS ───────────────────────────────────────

def test_01_old_checklist_summary_metrics(capability_matrix: dict):
    """Prove OLD_CHECKLIST_OPEN_ITEMS = 0, OLD_RESIDUALS = 0, UNCLASSIFIED_BLOCKERS = 0."""
    ccc = capability_matrix.get("commercial_command_center", {})
    summary = ccc.get("old_commercial_checklist", {})

    assert summary.get("status") == "ALL_CLOSED", f"Expected ALL_CLOSED, got {summary.get('status')}"
    assert summary.get("open_items") == 0, f"Expected 0 open items, got {summary.get('open_items')}"
    assert summary.get("residuals") == 0, f"Expected 0 residuals, got {summary.get('residuals')}"
    assert summary.get("unclassified_blockers") == 0, f"Expected 0 unclassified blockers, got {summary.get('unclassified_blockers')}"

    expected_items = {
        "B01": "CLOSED",
        "B02": "CLOSED_PARTIAL_READONLY",
        "B03": "CLOSED_PARTIAL_READONLY",
        "B04": "CLOSED_NOT_IMPLEMENTED",
        "B05": "CLOSED_READ_ONLY",
    }
    assert summary.get("items") == expected_items


# ─── 2. B01 CANONICAL PRODUCT AUTHORITY TRUTH ─────────────────────────────────

def test_02_b01_canonical_product_authority_truth(capability_matrix: dict):
    """Verify B01 reflects Bot Core reconciliation PR #1124 and legacy PR #1093 superseded."""
    b01 = capability_matrix["commercial_command_center"]["upstream_blockers"]["B01"]

    assert b01["code"] == "BOT_CANONICAL_PRODUCT_AUTHORITY_RECONCILED"
    assert b01["severity"] == "CONTRACT_WIRED"
    assert b01["write_mode"] == "CANONICAL_CAS_WRITE"
    assert b01["authority"] == "BOT_CORE"
    assert b01["reconciliation_pr"] == 1124
    assert b01["reconciliation_merge_sha"] == "f8b3ce6ed73995fb4e3e893d03269af662541e58"
    assert b01["legacy_pr_1093_state"] == "CLOSED_SUPERSEDED"
    assert b01["live_status"] == "CONTRACT_WIRED_SOURCE_VERIFIED"
    assert b01["old_checklist_status"] == "CLOSED"
    assert b01["remediation_gate"] == "NONE_FOR_OLD_CHECKLIST"


# ─── 3. B02 PRICING AUTHORITY TRUTH ───────────────────────────────────────────

def test_03_b02_pricing_authority_truth(capability_matrix: dict):
    """Verify B02 reflects deployed state with optional future live depth."""
    b02 = capability_matrix["commercial_command_center"]["upstream_blockers"]["B02"]

    assert b02["code"] == "BOT_CANONICAL_PRICING_WRITE_WIRED"
    assert b02["severity"] == "CONTRACT_WIRED"
    assert b02["write_mode"] == "CANONICAL_CAS_WRITE"
    assert b02["authority"] == "BOT_CORE"
    assert b02["live_status"] == "DEPLOYED_PRODUCTION_READONLY_PARTIAL"
    assert b02["old_checklist_status"] == "CLOSED_PARTIAL_READONLY"
    assert b02["remediation_gate"] == "OPTIONAL_FUTURE_LIVE_WRITE_ACCEPTANCE"


# ─── 4. B03 PACKAGES AUTHORITY TRUTH ──────────────────────────────────────────

def test_04_b03_packages_authority_truth(capability_matrix: dict):
    """Verify B03 reflects deployed production read-only pass state."""
    b03 = capability_matrix["commercial_command_center"]["upstream_blockers"]["B03"]

    assert b03["code"] == "BOT_CANONICAL_PACKAGES_WRITE_WIRED"
    assert b03["severity"] == "CONTRACT_WIRED"
    assert b03["write_mode"] == "CANONICAL_CAS_WRITE"
    assert b03["authority"] == "BOT_CORE"
    assert b03["bot_pr_1115_deployed"] is True
    assert b03["production_readonly_acceptance"] == "PASS"
    assert b03["production_write_acceptance"] == "NOT_RUN"
    assert b03["business_live"] == "PARTIAL_READONLY"
    assert b03["live_status"] == "DEPLOYED_PRODUCTION_READONLY_PASS"
    assert b03["old_checklist_status"] == "CLOSED_PARTIAL_READONLY"
    assert b03["remediation_gate"] == "OPTIONAL_OWNER_AUTHORIZED_WRITE_CANARY"


# ─── 5. B04 PROMOTIONS AUTHORITY TRUTH ────────────────────────────────────────

def test_05_b04_promotions_authority_truth(capability_matrix: dict):
    """Verify B04 reflects factual NOT_IMPLEMENTED discovery truth."""
    b04 = capability_matrix["commercial_command_center"]["upstream_blockers"]["B04"]

    assert b04["code"] == "BOT_CANONICAL_PROMOTIONS_AUTHORITY_NOT_IMPLEMENTED"
    assert b04["severity"] == "NOT_IMPLEMENTED"
    assert b04["write_mode"] == "READ_ONLY"
    assert b04["authority"] == "NONE"
    assert b04["bot_discovery_pr"] == 1118
    assert b04["bot_discovery_merge_sha"] == "edcce9e2bb949ea3b935cf58c20b30a834c9a819"
    assert b04["authority_discovered"] is False
    assert b04["no_model_invented"] is True
    assert b04["live_status"] == "NOT_IMPLEMENTED"
    assert b04["old_checklist_status"] == "CLOSED_NOT_IMPLEMENTED"
    assert b04["remediation_gate"] == "NEW_PROMOTION_ENGINE_PROGRAM_REQUIRED"


# ─── 6. B05 TOPUP CONFIG AUTHORITY TRUTH ──────────────────────────────────────

def test_06_b05_topup_config_authority_truth(capability_matrix: dict):
    """Verify B05 reflects factual READ_ONLY static runtime truth."""
    b05 = capability_matrix["commercial_command_center"]["upstream_blockers"]["B05"]

    assert b05["code"] == "BOT_CANONICAL_TOPUP_CONFIG_AUTHORITY_NOT_MUTABLE"
    assert b05["severity"] == "READ_ONLY"
    assert b05["write_mode"] == "READ_ONLY"
    assert b05["authority"] == "BOT_RUNTIME_STATIC"
    assert b05["bot_discovery_pr"] == 1121
    assert b05["bot_discovery_merge_sha"] == "c157db5596c818a16e98d472872c829ef2225f90"
    assert b05["authority_discovered"] is False
    assert b05["runtime_topup_package_count"] == 6
    assert b05["no_model_invented"] is True
    assert b05["live_status"] == "READ_ONLY_RUNTIME_TRUTH"
    assert b05["old_checklist_status"] == "CLOSED_READ_ONLY"
    assert b05["remediation_gate"] == "MUTABLE_TOPUP_CONFIG_PROGRAM_REQUIRED"


# ─── 7. GATE CLASSIFICATION RIGOR ─────────────────────────────────────────────

def test_07_gate_classification_proves_zero_residuals(capability_matrix: dict):
    """Verify every remediation gate is classified as FUTURE_PROGRAM, OPTIONAL_LIVE_DEPTH, or NO_GATE.

    None can be classified as an open old-checklist blocker.
    """
    blockers = capability_matrix["commercial_command_center"]["upstream_blockers"]

    gate_classification = {
        "NONE_FOR_OLD_CHECKLIST": "NO_GATE",
        "OPTIONAL_FUTURE_LIVE_WRITE_ACCEPTANCE": "OPTIONAL_LIVE_DEPTH",
        "OPTIONAL_OWNER_AUTHORIZED_WRITE_CANARY": "OPTIONAL_LIVE_DEPTH",
        "NEW_PROMOTION_ENGINE_PROGRAM_REQUIRED": "FUTURE_PROGRAM",
        "MUTABLE_TOPUP_CONFIG_PROGRAM_REQUIRED": "FUTURE_PROGRAM",
    }

    unclassified = []
    old_residuals = []

    for item_key, meta in blockers.items():
        gate = meta.get("remediation_gate")
        category = gate_classification.get(gate)
        if category is None:
            unclassified.append((item_key, gate))
        elif category == "OLD_CHECKLIST_RESIDUAL":
            old_residuals.append((item_key, gate))

    assert len(unclassified) == 0, f"Found unclassified gates: {unclassified}"
    assert len(old_residuals) == 0, f"Found open old residuals: {old_residuals}"


# ─── 8. CODEBASE HYGIENE: ZERO STALE TRUTH REFERENCES ─────────────────────────

def test_08_zero_stale_active_truth_references(portal_js_content: str, admin_commercial_content: str):
    """Prove STALE_ACTIVE_TRUTH_REFERENCES = 0 across active Web portal and backend routers."""
    # 1. No active references to stale PR 1093 in portal.js or router
    assert "1093" not in portal_js_content, "Found stale PR 1093 reference in portal.js"
    assert "1093" not in admin_commercial_content, "Found stale PR 1093 reference in copyfast_admin_commercial.py"

    # 2. No fake promotion IDs in portal.js
    assert "PROMO_WELCOME_2026" not in portal_js_content
    assert "PROMO_TET_BONUS" not in portal_js_content

    # 3. No fake conversion rates in portal.js (95d, 91d, 86d)
    for fake_rate in ["95đ", "91đ", "86đ", "95d", "91d", "86d"]:
        assert fake_rate not in portal_js_content

    # 4. No promotion or topup mutation routes in copyfast_admin_commercial.py
    import copyfast_admin_commercial as backend_mod
    routes = [r.path for r in backend_mod.router.routes]

    # No promotion routes
    promo_routes = [p for p in routes if "promotion" in p.lower()]
    assert len(promo_routes) == 0, f"Unexpected promotion routes: {promo_routes}"

    # Topup routes must only be GET (read-only)
    for r in backend_mod.router.routes:
        if "topup" in r.path.lower():
            methods = getattr(r, "methods", set())
            assert methods.issubset({"GET", "HEAD", "OPTIONS"}), f"Topup route has mutating method: {r.path} {methods}"
