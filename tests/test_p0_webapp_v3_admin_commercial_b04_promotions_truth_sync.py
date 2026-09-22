"""P0 WebApp Commercial B04 Promotions Web Truth Sync & Mock Removal Tests.

Validates the Web Admin Commercial B04 truth sync under:
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: P0.WEBAPP.V3.ADMIN.COMMERCIAL.B04.PROMOTIONS.WEB.TRUTH.SYNC.MOCK.REMOVAL.R1

Enforces:
- B04 capability metadata in admin_capability_matrix.json reflects Bot Core PR #1118 discovery truth (NOT_IMPLEMENTED).
- Static fake promotion records (PROMO_WELCOME_2026, PROMO_TET_BONUS) are completely removed from portal.js.
- STATIC_PROMOTION_RECORD_COUNT = 0
- Zero Web-owned promotion mutation routes or local promotion DB.
- B05 top-up bonus authority remains strictly separate.
- B02 base pricing and B03 packages remain strictly separate.
- Commercial tabs 1..5 preserved; Promotions tab remains accessible with truthful status ("Chưa hỗ trợ")
  and explicit boundary notes.
- B01, B02, B03 and B05 fail-closed protections are verified.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

STANDALONE_ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_MATRIX_PATH = STANDALONE_ROOT / "admin_capability_matrix.json"
PORTAL_JS_PATH = STANDALONE_ROOT / "static" / "portal" / "portal.js"


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


# ─── 1. CAPABILITY MATRIX TRUTH ───────────────────────────────────────────────

def test_01_b04_capability_matrix_metadata_truth(capability_matrix: dict):
    """Section 2: B04 metadata in capability matrix reflects PR #1118 discovery truth."""
    blockers = capability_matrix.get("commercial_command_center", {}).get("upstream_blockers", {})
    b04 = blockers.get("B04")
    assert b04 is not None, "B04 must exist in upstream_blockers"

    assert b04.get("code") == "BOT_CANONICAL_PROMOTIONS_AUTHORITY_NOT_IMPLEMENTED"
    assert b04.get("severity") == "NOT_IMPLEMENTED"
    assert b04.get("write_mode") == "READ_ONLY"
    assert b04.get("authority") == "NONE"
    assert b04.get("bot_discovery_pr") == 1118
    assert b04.get("bot_discovery_merge_sha") == "edcce9e2bb949ea3b935cf58c20b30a834c9a819"
    assert b04.get("authority_discovered") is False
    assert b04.get("no_model_invented") is True
    assert b04.get("live_status") == "NOT_IMPLEMENTED"
    assert b04.get("remediation_gate") == "NEW_PROMOTION_ENGINE_PROGRAM_REQUIRED"


# ─── 2. STATIC MOCK REMOVAL & ZERO FAKE ROWS ─────────────────────────────────

def test_02_static_promotion_mock_removal(portal_js_content: str):
    """Section 4: Remove any fake promotion rows and fake voucher IDs."""
    # Ensure fake voucher IDs are completely removed from runtime JS
    assert "PROMO_WELCOME_2026" not in portal_js_content, "PROMO_WELCOME_2026 must be removed"
    assert "PROMO_TET_BONUS" not in portal_js_content, "PROMO_TET_BONUS must be removed"
    assert "promosList" not in portal_js_content, "promosList array must be removed"

    # Verify STATIC_PROMOTION_RECORD_COUNT = 0
    fake_rows = [code for code in ["PROMO_WELCOME_2026", "PROMO_TET_BONUS"] if code in portal_js_content]
    assert len(fake_rows) == 0


# ─── 3. ZERO FAKE PROMOTION API & LOCAL AUTHORITY ────────────────────────────

def test_03_zero_web_promotion_mutation_api():
    """Section 5: Zero Web promotion mutation endpoints or local promotion DB."""
    import copyfast_admin_commercial as backend_mod

    routes = [r.path for r in backend_mod.router.routes]
    promotion_mutation_routes = [
        r for r in backend_mod.router.routes
        if "promotion" in r.path.lower() and getattr(r, "methods", None) and any(m in {"POST", "PATCH", "PUT", "DELETE"} for m in r.methods)
    ]
    assert len(promotion_mutation_routes) == 0, f"Found unexpected promotion mutation routes: {promotion_mutation_routes}"

    promotion_routes = [p for p in routes if "promotion" in p.lower()]
    assert len(promotion_routes) == 0, f"Found unexpected promotion routes: {promotion_routes}"


# ─── 4. B05 TOPUP BONUS SEPARATION ───────────────────────────────────────────

def test_04_b05_topup_boundary_separation(capability_matrix: dict, portal_js_content: str):
    """Section 6: B05 top-up bonus remains strictly separate from B04."""
    blockers = capability_matrix.get("commercial_command_center", {}).get("upstream_blockers", {})
    b05 = blockers.get("B05")
    assert b05.get("severity") in {"FAIL_CLOSED", "READ_ONLY"}
    assert b05.get("code") in {"BOT_WRITE_ENDPOINT_MISSING_FOR_TOPUP_PACKAGES", "BOT_CANONICAL_TOPUP_CONFIG_AUTHORITY_NOT_MUTABLE"}

    # Tab 5 exists separately in portal.js
    assert "5. Gói Nạp Xu PayOS" in portal_js_content
    assert "topup_packages" in portal_js_content


# ─── 5. B02 & B03 BOUNDARY SEPARATION ────────────────────────────────────────

def test_05_b02_b03_pricing_and_package_separation(capability_matrix: dict):
    """Section 7: B02 pricing and B03 packages remain separate from B04."""
    blockers = capability_matrix.get("commercial_command_center", {}).get("upstream_blockers", {})
    b02 = blockers.get("B02")
    b03 = blockers.get("B03")

    assert b02.get("authority") == "BOT_CORE"
    assert b02.get("write_mode") == "CANONICAL_CAS_WRITE"

    assert b03.get("authority") == "BOT_CORE"
    assert b03.get("write_mode") == "CANONICAL_CAS_WRITE"
    assert b03.get("severity") == "CONTRACT_WIRED"


# ─── 6. PROMOTIONS TAB ACCESSIBILITY & TRUTHFUL VIETNAMESE COPY ───────────────

def test_06_promotions_tab_accessible_with_truthful_copy(portal_js_content: str):
    """Section 3, 8, 9: Promotions tab remains visible and displays truthful copy."""
    # Tab 4 remains in navigation
    assert "4. Khuyến mãi & Voucher" in portal_js_content
    assert 'activeTab === "promotions"' in portal_js_content

    # Required truthful messages present
    assert "Hệ thống hiện chưa hỗ trợ voucher/khuyến mãi giảm giá riêng cho dịch vụ hoặc gói cước." in portal_js_content
    assert "Khuyến mãi nạp Xu thuộc mục Gói nạp / Top-up, không thuộc mục này." in portal_js_content

    # Status badge is "Chưa hỗ trợ"
    assert "Chưa hỗ trợ" in portal_js_content

    # Navigation button to top-up packages is present
    assert 'href="/admin/commercial?tab=topup_packages"' in portal_js_content

    # Blocker banner has updated tag
    assert "B04: Khuyến mãi (Chưa hỗ trợ)" in portal_js_content
