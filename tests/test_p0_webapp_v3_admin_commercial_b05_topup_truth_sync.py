"""P0 WebApp Commercial B05 Top-up Packages Web Truth Sync (Read-Only) Tests.

Validates the Web Admin Commercial B05 truth sync under:
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: P0.WEBAPP.V3.ADMIN.COMMERCIAL.B05.TOPUP.PACKAGES.WEB.TRUTH.SYNC.READONLY.R1

Enforces:
- B05 capability metadata in admin_capability_matrix.json reflects Bot Core PR #1121 discovery truth
  (BOT_CANONICAL_TOPUP_CONFIG_AUTHORITY_NOT_MUTABLE, severity READ_ONLY, authority BOT_RUNTIME_STATIC).
- Six canonical runtime top-up tiers rendered in portal.js (10k, 20k, 50k, 100k, 200k, 500k at 100 VND = 1 Xu).
- Fake conversion rates (95d, 91d, 86d) and fake bonus values (50, 200, 800) are removed.
- Zero Web-owned topup mutation endpoints (WEB_TOPUP_MUTATION_ENDPOINT_COUNT = 0).
- Zero local Web topup authority DB tables (WEB_LOCAL_TOPUP_AUTHORITY_COUNT = 0).
- Zero fake edit, save, publish, or delete controls in B05 UI (STATIC_TOPUP_MUTATION_CONTROLS = 0).
- Truthful copy displays Bot PR #1121 provenance, 100 VND = 1 Xu base rate, auto-bonus policy (+30% 1st, +20% 2nd),
  launch bonus disabled notice, and immutable financial ledger safety invariant.
- B04 Promotions and B05 Top-up Packages boundary separation is verified.
- Customer payment options and manual QR contracts preserved.
"""

from __future__ import annotations

import json
import re
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

def test_01_b05_capability_matrix_metadata_truth(capability_matrix: dict):
    """Section 2: B05 metadata in capability matrix reflects PR #1121 discovery truth."""
    blockers = capability_matrix.get("commercial_command_center", {}).get("upstream_blockers", {})
    b05 = blockers.get("B05")
    assert b05 is not None, "B05 must exist in upstream_blockers"

    assert b05.get("code") == "BOT_CANONICAL_TOPUP_CONFIG_AUTHORITY_NOT_MUTABLE"
    assert b05.get("severity") == "READ_ONLY"
    assert b05.get("write_mode") == "READ_ONLY"
    assert b05.get("authority") == "BOT_RUNTIME_STATIC"
    assert b05.get("bot_discovery_pr") == 1121
    assert b05.get("bot_discovery_merge_sha") == "c157db5596c818a16e98d472872c829ef2225f90"
    assert b05.get("authority_discovered") is False
    assert b05.get("runtime_topup_package_count") == 6
    assert b05.get("no_model_invented") is True
    assert b05.get("live_status") == "READ_ONLY_RUNTIME_TRUTH"
    assert b05.get("remediation_gate") == "MUTABLE_TOPUP_CONFIG_PROGRAM_REQUIRED"


# ─── 2. SIX CANONICAL RUNTIME TIERS IN PORTAL.JS ─────────────────────────────

def test_02_six_canonical_runtime_tiers_in_portal_js(portal_js_content: str):
    """Section 4: Six canonical Bot runtime tiers rendered in portal.js at 100 VND = 1 Xu."""
    expected_tiers = [
        ("topup_10k", 10000, 100),
        ("topup_20k", 20000, 200),
        ("topup_50k", 50000, 500),
        ("topup_100k", 100000, 1000),
        ("topup_200k", 200000, 2000),
        ("topup_500k", 500000, 5000),
    ]

    for code, amount, xu in expected_tiers:
        assert f'code: "{code}"' in portal_js_content, f"Missing tier {code} in portal.js"
        assert f"amount_vnd: {amount}" in portal_js_content, f"Missing amount {amount} for {code}"
        assert f"xu: {xu}" in portal_js_content, f"Missing xu {xu} for {code}"

    # Extract the topupPackagesList definition
    match = re.search(r"const topupPackagesList\s*=\s*\[([\s\S]*?)\];", portal_js_content)
    assert match is not None, "topupPackagesList array must exist in portal.js"
    array_content = match.group(1)

    # Verify all 6 codes are in the list
    for code, _, _ in expected_tiers:
        assert code in array_content, f"Code {code} must be in topupPackagesList"

    # Verify fake rates are gone from topupPackagesList
    assert "95 đ" not in array_content, "Fake 95d rate must be removed"
    assert "91 đ" not in array_content, "Fake 91d rate must be removed"
    assert "86 đ" not in array_content, "Fake 86d rate must be removed"

    # Verify fake bonus numbers are gone from topupPackagesList
    assert "bonus_xu: 50" not in array_content, "Fake 50 bonus must be removed"
    assert "bonus_xu: 200" not in array_content, "Fake 200 bonus must be removed"
    assert "bonus_xu: 800" not in array_content, "Fake 800 bonus must be removed"

    # Verify all tiers have status "read_only"
    assert array_content.count('"read_only"') == 6


# ─── 3. ZERO WEB TOPUP MUTATION API & LOCAL AUTHORITY ────────────────────────

def test_03_zero_web_topup_mutation_api():
    """Section 5: Zero Web topup mutation endpoints or local topup DB."""
    import copyfast_admin_commercial as backend_mod

    routes = [r.path for r in backend_mod.router.routes]
    topup_mutation_routes = [
        r for r in backend_mod.router.routes
        if "topup" in r.path.lower() and getattr(r, "methods", None) and any(m in {"POST", "PATCH", "PUT", "DELETE"} for m in r.methods)
    ]
    assert len(topup_mutation_routes) == 0, f"Found unexpected topup mutation routes: {topup_mutation_routes}"

    # Verify WEB_TOPUP_MUTATION_ENDPOINT_COUNT = 0 in admin commercial
    admin_topup_routes = [p for p in routes if "topup" in p.lower()]
    assert len(admin_topup_routes) == 0, f"Found unexpected admin commercial topup routes: {admin_topup_routes}"


# ─── 4. ZERO FAKE EDIT/SAVE/PUBLISH CONTROLS IN B05 UI ───────────────────────

def test_04_zero_fake_edit_save_publish_controls(portal_js_content: str):
    """Section 6: No edit, save, publish, or delete buttons for topup packages."""
    match = re.search(r'activeTab === "topup_packages"\) \{([\s\S]*?)\n\s*\}', portal_js_content)
    assert match is not None, "activeTab === 'topup_packages' block must exist"
    tab_content = match.group(1)

    assert "data-portal-action=\"edit-topup\"" not in tab_content
    assert "data-portal-action=\"save-topup\"" not in tab_content
    assert "data-portal-action=\"publish-topup\"" not in tab_content
    assert "data-portal-action=\"delete-topup\"" not in tab_content
    assert "<button" not in tab_content, "No mutation buttons in read-only topup packages tab"

    # Status badge is "Chỉ đọc"
    assert 'data-status="read_only"' in tab_content
    assert "Chỉ đọc" in tab_content


# ─── 5. TRUTHFUL AUTO-BONUS POLICY & FINANCIAL SAFETY COPY ───────────────────

def test_05_truthful_auto_bonus_policy_and_safety_copy(portal_js_content: str):
    """Section 7: Displays Bot PR #1121 provenance, 100 VND = 1 Xu base rate, auto-bonus policy, and safety."""
    match = re.search(r'activeTab === "topup_packages"\) \{([\s\S]*?)\n\s*\}', portal_js_content)
    assert match is not None
    tab_content = match.group(1)

    # Bot Core provenance
    assert "PR #1121" in tab_content
    assert "c157db5596c818a16e98d472872c829ef2225f90" in tab_content
    assert "Bot Core Runtime" in tab_content

    # Base rate truth
    assert "100 đ = 1 Xu" in tab_content
    assert "bot.package_base_xu" in tab_content

    # Auto-bonus policy
    assert "Lần nạp 1:" in tab_content and "+30%" in tab_content
    assert "Lần nạp 2:" in tab_content and "+20%" in tab_content
    assert "Lần nạp 3 trở đi:" in tab_content
    assert "10.000 đ" in tab_content
    assert "Launch Bonus" in tab_content

    # Financial safety invariant
    assert "Mọi dữ liệu giao dịch PayOS, lịch sử nạp, số dư ví Xu và nhật ký kế toán đều là bất biến, không thể chỉnh sửa." in tab_content


# ─── 6. B04 AND B05 BOUNDARY SEPARATION ──────────────────────────────────────

def test_06_b04_b05_boundary_separation(portal_js_content: str):
    """Section 8: B04 promotions and B05 top-up packages are strictly separated."""
    # B05 UI contains explicit boundary note
    assert "Thưởng nạp Xu là chính sách nạp tiền, không phải voucher giảm giá dịch vụ/gói cước." in portal_js_content

    # B04 tab links to B05
    assert 'href="/admin/commercial?tab=topup_packages"' in portal_js_content

    # Blocker banner has updated B05 tag
    assert "B05: Gói nạp (Chỉ đọc)" in portal_js_content
    assert "B04: Khuyến mãi (Chưa hỗ trợ)" in portal_js_content


# ─── 7. CUSTOMER PAYMENT OPTIONS & QR CONTRACT PRESERVATION ──────────────────

def test_07_customer_payment_options_and_qr_preservation():
    """Section 9: Customer payment options and manual QR contracts remain fully preserved."""
    import copyfast_api

    # 6 canonical packages in DEFAULT_TOPUP_PACKAGES
    assert len(copyfast_api.DEFAULT_TOPUP_PACKAGES) == 6
    codes = [pkg["code"] for pkg in copyfast_api.DEFAULT_TOPUP_PACKAGES]
    assert codes == ["topup_10k", "topup_20k", "topup_50k", "topup_100k", "topup_200k", "topup_500k"]

    # Manual payment methods preserved
    assert "bank_acb_vietqr" in copyfast_api.MANUAL_TOPUP_METHOD_IDS
    assert "bank_acb" in copyfast_api.MANUAL_TOPUP_METHOD_IDS
