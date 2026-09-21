"""First-Red Contract Verification Suite for P0.WEBAPP.V3.FULL.PRODUCT.ADMIN.COMMERCIAL.UX.TRUTH.REMEDIATION.R1.

Verifies the empirical FIRST RED proof matrix on PRE_HEAD (670fb4a) before remediation.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
FIRST_RED_MATRIX_PATH = ROOT / "tests" / "first_red_matrix.json"


@pytest.fixture
def first_red_data() -> dict:
    assert FIRST_RED_MATRIX_PATH.exists(), "FIRST RED matrix file must exist"
    return json.loads(FIRST_RED_MATRIX_PATH.read_text(encoding="utf-8"))


def test_first_red_matrix_coordinates(first_red_data: dict) -> None:
    """Verify task and commit coordinates."""
    assert first_red_data["task"] == "P0.WEBAPP.V3.FULL.PRODUCT.ADMIN.COMMERCIAL.UX.TRUTH.REMEDIATION.R1"
    assert first_red_data["pre_head"] == "670fb4aa0106f615cc4607b14c21243da416e265"
    assert first_red_data["bot_reference_sha"] == "e0ce16e5d4ba6816d4f5205aad662eba8c635045"


def test_first_red_all_17_gaps_proven(first_red_data: dict) -> None:
    """Verify all 17 gaps were proven red on PRE_HEAD."""
    matrix = first_red_data["first_red_matrix"]
    assert len(matrix) == 17, f"Expected 17 gaps in matrix, got {len(matrix)}"

    assert matrix["CUSTOMER_PRIMARY_NAV_BOT_ALIGNED"] == "NO"
    assert matrix["REDUNDANT_WORKSPACES"] > 0
    assert matrix["DUPLICATE_PRODUCT_SURFACES"] > 0
    assert matrix["PLANNING_ONLY_PRODUCT_SURFACES"] > 0
    assert matrix["READ_ONLY_PRODUCT_SUBSTITUTES"] > 0
    assert matrix["GUARDED_PRODUCT_SURFACES"] > 0
    assert matrix["BOT_FUNCTION_WITHOUT_REAL_WEB_EXECUTION"] > 0
    assert matrix["NORMAL_USER_INTERNAL_JARGON_VISIBLE"] > 0
    assert matrix["DASHBOARD_PRODUCT_FIRST"] == "NO"
    assert matrix["ADMIN_PRODUCT_EDITOR_REAL"] == "NO"
    assert matrix["ADMIN_EFFECTIVE_PRICE_CONTROL"] == "NO"
    assert matrix["ADMIN_PACKAGE_REAL_WRITE"] == "NO"
    assert matrix["ADMIN_PROMO_REAL_WRITE"] == "NOT_PROVEN"
    assert matrix["ADMIN_TOPUP_PACKAGE_REAL_WRITE"] == "NO"
    assert matrix["ADMIN_COMMERCIAL_CONTROL_COMPLETE"] == "NO"
    assert matrix["TOPUP_QR_PRIMARY_VISUAL"] == "NO"
    assert matrix["TOPUP_QR_TOO_SMALL"] == "YES"


def test_first_red_empirical_evidence_documented(first_red_data: dict) -> None:
    """Verify empirical proof documentation."""
    proofs = first_red_data["empirical_proofs"]
    assert len(proofs) >= 7
    for key, proof in proofs.items():
        assert len(proof) > 10, f"Proof for {key} is too brief"
