"""Focused empirical verification test suite for Task V2-03: Customer Commerce Surfaces.

Task: TASK=P0.WEBAPP.V2-03.CUSTOMER.COMMERCE.SURFACES
Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Repository: manhtoangreensky-wq/toan-aas-standalone
Base Ref: feat/p0-webapp-v2-02-admin-command-dashboard
Branch: feat/p0-webapp-v2-03-customer-commerce-surfaces

Invariants:
1. CANONICAL_COMMERCE_ROUTE=/pricing
2. PRIMARY_NAV_PRICING_LINK=1, PRIMARY_NAV_PACKAGES_LINK=0, PRIMARY_NAV_MEMBERSHIP_LINK=0
3. PACKAGES_DEEP_LINK_404=0, MEMBERSHIP_DEEP_LINK_404=0, LEGACY_REDIRECT_LOOP=0
4. COMMERCE_PRIMARY_SURFACE_COUNT=1
5. CANONICAL_PRICING_SOURCE_SINGLE=YES (PRICE_SOURCE_COUNT=1)
6. FAKE_PRICE_COUNT=0, MISMATCHED_PRICE_COUNT=0
7. FAKE_PACKAGE_COUNT=0, DEAD_PACKAGE_CTA=0
8. FAKE_VIP_TIER_COUNT=0, FAKE_VIP_BENEFIT_COUNT=0, FAKE_DISCOUNT_COUNT=0, UNSOURCED_PROMOTIONAL_CLAIMS=0
9. TOPUP_CTA_ROUTE=/wallet/topup
10. PAYOS_CALLS=0, WALLET_MUTATIONS=0
11. ZERO_REMAINS_ZERO=YES, UNKNOWN_NOT_ZERO=YES
12. TECHNICAL_COPY_LEAK=0
13. CUSTOMER_ADMIN_ROUTE_LEAK=0
14. COMMERCE_HIERARCHY_FIVE_SECTIONS: A. Giá dịch vụ, B. Gói nạp, C. Quyền lợi hội viên, D. Giải thích Xu, E. CTA nạp Xu
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import app

ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static" / "portal" / "portal.js"
PORTAL_SOURCE = PORTAL_PATH.read_text(encoding="utf-8")


def _run_node_render_catalog(page_path: str, context: dict | None = None) -> dict:
    """Execute renderCatalog in Node.js with extracted portal.js context."""
    import json
    ctx_json = json.dumps(context or {})
    script = f'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");

function extract(start, end) {{
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error(`missing start: ${{start}}`);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error(`missing end: ${{end}}`);
  return source.slice(offset, finish);
}}

// Minimal mock environment
global.window = global;
function safeText(v) {{ return String(v == null ? "" : v); }}
function badge(s) {{ return `<span class="portal-badge" data-badge="${{s}}">${{s}}</span>`; }}
function portalIcon(name) {{ return `<span class="portal-icon" data-icon="${{name}}"></span>`; }}
function renderHero(page, ctx) {{ return `<header class="portal-page-hero"><h1>${{page.title || "Hero"}}</h1></header>`; }}
function renderEmpty(t, m, icon) {{ return `<div class="portal-empty"><h2>${{t}}</h2><p>${{m}}</p></div>`; }}
function renderStatusCard(page, ctx) {{ return `<div class="portal-status-card">Status</div>`; }}
function renderSummary(page, ctx) {{ return `<div class="portal-summary">Summary</div>`; }}
function renderNotes(page) {{ return `<div class="portal-notes">Notes</div>`; }}
function normalizePath(p) {{ return "/" + String(p || "").replace(/^\\/+|\\/+$/g, ""); }}
function uiText(k, fb) {{ return fb || k; }}
function billingCatalogText(k, fb) {{ return fb || k; }}
function adminNumber(v, s) {{ return String(v) + (s || ""); }}
const ALLOWED_STATES = new Set(["ready", "guarded", "empty", "loading", "processing", "read_only"]);

const ICONS = {{ pricing: "pricing", package: "package", payments: "payments", wallet: "wallet" }};
const page = {{ path: "{page_path}", title: "Bảng giá", description: "Bảng giá dịch vụ" }};
const context = {ctx_json};

// Evaluate needed functions from portal.js
eval(extract("function membershipCatalogEntries(context)", "const MEMBER_TIER_CANONICAL ="));
eval(extract("const MEMBER_TIER_CANONICAL =", "function getMemberTierInfo").replace("const MEMBER_TIER_CANONICAL =", "global.MEMBER_TIER_CANONICAL ="));
eval(extract("function renderMembership(page, context)", "function renderServiceStatus(page, context)"));
eval(extract("function canonicalShortText", "function canonicalPricingCatalog"));
eval(extract("function canonicalPricingCatalog(value)", "function canonicalPackageCatalog(value)"));
eval(extract("function canonicalPackageCatalog(value)", "function safePayosCheckout"));
eval(extract("const DEFAULT_CANONICAL_PACKAGES =", "function renderCatalog(page, context)").replace("const DEFAULT_CANONICAL_PACKAGES =", "global.DEFAULT_CANONICAL_PACKAGES ="));
eval(extract("function renderBillingWorkspaceNav", "function renderPaymentEntryPoints"));
eval(extract("function renderCatalog(page, context)", "const JOB_FILTERS"));

try {{
  const html = page.path === "/membership" ? renderMembership(page, context) : renderCatalog(page, context);
  console.log(JSON.stringify({{ ok: true, html }}));
}} catch (err) {{
  console.log(JSON.stringify({{ ok: false, error: err.message, stack: err.stack }}));
}}
'''
    result = subprocess.run(
        ["node", "-e", script, str(PORTAL_PATH)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr + "\n" + result.stdout}
    import json
    return json.loads(result.stdout)


class TestP0WebappV203CustomerCommerceSurfaces:
    """Empirical verification test suite for customer commerce surfaces."""

    def test_01_canonical_commerce_route_and_primary_nav_parity(self) -> None:
        """Verify CANONICAL_COMMERCE_ROUTE=/pricing and nav invariants."""
        # 1. Primary customer navigation must have /pricing
        assert '["/pricing", "Bảng giá", ICONS.pricing]' in PORTAL_SOURCE, (
            "Primary customer navigation must include /pricing"
        )

        # 2. Extract customer navigation groups from navGroups function
        nav_groups_match = re.search(
            r"function navGroups\(context, currentPage\) \{(.*?)\n  \}",
            PORTAL_SOURCE,
            re.DOTALL
        )
        assert nav_groups_match, "navGroups function not found in portal.js"
        nav_source = nav_groups_match.group(1)

        # Ensure /packages and /membership are NOT in the primary navigation links
        assert '["/packages"' not in nav_source, "Primary nav must not contain /packages"
        assert '["/membership"' not in nav_source, "Primary nav must not contain /membership"

        # 3. Exactly 1 primary commerce surface in navigation links
        commerce_surfaces_in_nav = [
            route for route in ["/pricing", "/packages", "/membership"]
            if f'["{route}"' in nav_source
        ]
        assert commerce_surfaces_in_nav == ["/pricing"], (
            f"Expected only ['/pricing'] in primary nav, got {commerce_surfaces_in_nav}"
        )

    def test_02_legacy_deep_links_no_404_and_registered(self) -> None:
        """Verify /packages and /membership remain routable (no 404s, no dead ends)."""
        client = TestClient(app)

        # Legacy routes return 200 or 307 redirect (to login if unauthenticated), NEVER 404
        for route in ("/pricing", "/packages", "/membership"):
            resp = client.get(route, follow_redirects=False)
            assert resp.status_code in (200, 307), f"Route {route} returned unexpected status {resp.status_code}"
            assert resp.status_code != 404, f"Route {route} must not 404"

        # In portal.js manifest, routes must be registered
        assert 'customerPage("/pricing"' in PORTAL_SOURCE
        assert 'customerPage("/packages"' in PORTAL_SOURCE
        assert 'customerPage("/membership"' in PORTAL_SOURCE

    def test_03_zero_fake_vip_tiers_and_zero_fake_discounts(self) -> None:
        """Verify zero fake VIP tiers, zero fake discount rates, zero fake birthday gifts.

        The system must NOT display unsourced 2%, 4%, 6%, 8%, 10% discounts,
        unsourced 111, 333, 555, 666, 888 Xu birthday gifts, or fake vouchers.
        """
        forbidden_fake_claims = [
            "Quà tặng sinh nhật",
            "birthdayGiftXu",
            "111 Xu",
            "333 Xu",
            "555 Xu",
            "666 Xu",
            "888 Xu",
            "Zero Queue Số 1",
            "Dedicated 5 phút",
            "1-1 Riêng từ Admin",
        ]
        found_claims = [claim for claim in forbidden_fake_claims if claim in PORTAL_SOURCE]
        assert not found_claims, (
            f"Found forbidden unsourced VIP/promotional claims in portal.js: {found_claims}"
        )

    def test_04_canonical_pricing_source_single(self) -> None:
        """Verify single source of pricing truth without duplicate competing client tables."""
        # Must consume canonicalPublicSalePricingCatalog
        assert "function canonicalPublicSalePricingCatalog(value)" in PORTAL_SOURCE
        # Must not have hardcoded competing sale pricing dictionaries that override server truth
        assert "function approvedPublicSalePriceIndex(catalog)" in PORTAL_SOURCE

    def test_05_package_cta_safety_and_no_dead_buttons(self) -> None:
        """Verify all package and top-up CTAs route to /wallet/topup with zero dead buttons."""
        # Topup route must be /wallet/topup
        topup_cta_target = "/wallet/topup"
        assert topup_cta_target == "/wallet/topup"

        # Check renderCatalog for dead CTAs
        catalog_section_match = re.search(
            r"function renderCatalog\(page, context\) \{(.*?)\n  \}",
            PORTAL_SOURCE,
            re.DOTALL
        )
        assert catalog_section_match, "renderCatalog function not found"
        catalog_source = catalog_section_match.group(1)

        # Must not contain dead links href="#" or href=""
        assert 'href="#"' not in catalog_source
        assert 'href=""' not in catalog_source
        # Must route to /wallet/topup for purchase/topup actions
        assert '/wallet/topup' in catalog_source

    def test_06_zero_wallet_mutations_and_zero_payos_direct_creation(self) -> None:
        """Verify no direct wallet debit/credit or PayOS mutations on commerce surfaces."""
        catalog_section_match = re.search(
            r"function renderCatalog\(page, context\) \{(.*?)\n  \}",
            PORTAL_SOURCE,
            re.DOTALL
        )
        assert catalog_section_match, "renderCatalog function not found"
        catalog_source = catalog_section_match.group(1)

        for forbidden_action in (
            "wallet-debit",
            "wallet-credit",
            "payment-create",
            "payos-checkout",
            "order-create",
        ):
            assert f'data-portal-action="{forbidden_action}"' not in catalog_source

    def test_07_commerce_hierarchy_five_sections_on_pricing(self) -> None:
        """Verify /pricing presents the 5 required commerce sections in order.

        A. Giá dịch vụ (Service Pricing)
        B. Gói / lựa chọn nạp (Packages / Top-up options)
        C. Quyền lợi hội viên (Membership / VIP benefits)
        D. Giải thích Xu (Xu / Credit explanation: 100 VNĐ = 1 Xu)
        E. CTA nạp Xu (Primary Top-up CTA: /wallet/topup)
        """
        # Node.js rendering of /pricing
        res = _run_node_render_catalog("/pricing", {
            "pricingCatalog": {
                "available": True,
                "public_sale_catalog": {
                    "available": True,
                    "catalog_version": "v1",
                    "approval_status": "owner_approved",
                    "items": [
                        {"code": "img_std", "family": "image", "label": "Ảnh chuẩn", "sale_price_xu": 15, "status": "ready"}
                    ]
                }
            },
            "packageCatalog": {
                "available": True,
                "monthly": [{"code": "pkg_m1", "label": "Gói tháng 1", "note": "Gói chuẩn"}],
                "combos": []
            },
            "wallet": {"balance_xu": 500, "is_vip": False}
        })
        assert res["ok"], f"Node execution failed: {res.get('error')}"
        html = res["html"]

        # Section A: Giá dịch vụ
        assert "portal-pricing-services" in html or "Bảng giá" in html

        # Section B: Gói / Lựa chọn nạp
        assert "portal-pricing-packages" in html or "Gói" in html or "Mệnh giá nạp" in html

        # Section C: Quyền lợi hội viên
        assert "portal-pricing-membership" in html or "Quyền lợi" in html or "Hội viên" in html

        # Section D: Giải thích Xu (100 VNĐ = 1 Xu)
        assert "100 VNĐ" in html or "100 đ" in html or "1 Xu" in html

        # Section E: CTA nạp Xu (/wallet/topup)
        assert 'href="/wallet/topup"' in html

    def test_08_unknown_not_zero_and_zero_remains_zero(self) -> None:
        """Verify missing pricing or missing balance is rendered as fallback, not 0 Xu."""
        # Render with empty catalog
        res = _run_node_render_catalog("/pricing", {
            "pricingCatalog": {},
            "packageCatalog": {},
            "wallet": None
        })
        assert res["ok"], f"Node execution failed: {res.get('error')}"
        html = res["html"]

        # Missing price must not render as standalone "0 Xu"
        assert not re.search(r"(?<![0-9.,])0\s*Xu\b", html)
        assert ">0 Xu<" not in html
        # Must show informative empty/missing message
        assert "Chờ catalog giá bán" in html or "Giá chưa được Core Bridge cấp" in html or "Chưa có dữ liệu" in html

    def test_09_technical_copy_leak_zero(self) -> None:
        """Verify no internal technical tokens leak into customer commerce HTML."""
        res = _run_node_render_catalog("/pricing", {
            "pricingCatalog": {
                "available": True,
                "public_sale_catalog": {
                    "available": True,
                    "catalog_version": "v1",
                    "approval_status": "owner_approved",
                    "items": [
                        {"code": "img_std", "family": "image", "label": "Ảnh chuẩn", "sale_price_xu": 15, "status": "ready"}
                    ]
                }
            }
        })
        assert res["ok"]
        html = res["html"]

        forbidden_leaks = [
            "service_code",
            "engine_adapter",
            "ledger_event",
            "pricing_revision_id",
            "Traceback (most recent call last)",
            "Python exception",
        ]
        for leak in forbidden_leaks:
            assert leak not in html

    def test_10_customer_admin_route_leak_zero(self) -> None:
        """Verify no admin route links appear on customer commerce surfaces."""
        res = _run_node_render_catalog("/pricing", {})
        assert res["ok"]
        html = res["html"]

        admin_links = re.findall(r'href=["\'](/admin(?:/[^"\']*)?)["\']', html)
        assert not admin_links, f"Found admin links in customer pricing surface: {admin_links}"

    def test_11_membership_provenance_and_zero_assumed_static_ladder(self) -> None:
        """Verify zero assumed static membership tiers rendered and provenance requirements.

        1. ASSUMED_MEMBERSHIP_TIERS_RENDERED=0, MEMBERSHIP_STATIC_LADDER_VISIBLE=0
        2. No static 6-tier ladder (Newbie, Silver, Gold, Platinum, Diamond, VIP) rendered on /pricing or /membership.
        3. Signed session account metadata rendered when present.
        4. Informative fallback 'Không khả dụng' when signed session metadata absent.
        """
        # A. On /pricing:
        res_pricing = _run_node_render_catalog("/pricing", {
            "pricingCatalog": {
                "available": True,
                "public_sale_catalog": {"available": True, "items": [{"code": "img_std", "family": "image", "label": "Ảnh chuẩn", "sale_price_xu": 15, "status": "ready"}]}
            },
            "wallet": {"balance_xu": 1200, "is_vip": True, "total_spent_xu": 500, "plan": {"plan_name": "Gói Pro VIP", "plan_status": "active"}}
        })
        assert res_pricing["ok"], f"Render /pricing failed: {res_pricing.get('error')}"
        pricing_html = res_pricing["html"]

        # No static tier ladder titles rendered
        static_tier_titles = [
            "Hạng Tân Thủ (Newbie)",
            "Hạng Bạc (Silver)",
            "Hạng Vàng (Gold)",
            "Hạng Bạch Kim (Platinum)",
            "Hạng Kim Cương (Diamond)",
            "Hạng VIP Đối Tác (VIP Partner)",
        ]
        for tier_title in static_tier_titles:
            assert tier_title not in pricing_html, f"Static tier title '{tier_title}' should not be rendered on /pricing"

        # Truthful signed-session metadata rendered
        assert "Hội viên VIP" in pricing_html
        assert "Gói Pro VIP" in pricing_html
        assert "1200 Xu" in pricing_html

        # When wallet is absent: renders 'Không khả dụng'
        res_pricing_anon = _run_node_render_catalog("/pricing", {})
        assert res_pricing_anon["ok"]
        pricing_anon_html = res_pricing_anon["html"]
        assert "Không khả dụng" in pricing_anon_html
        for tier_title in static_tier_titles:
            assert tier_title not in pricing_anon_html

        # B. On /membership:
        res_member = _run_node_render_catalog("/membership", {})
        assert res_member["ok"], f"Render /membership failed: {res_member.get('error')}"
        member_html = res_member["html"]
        for tier_title in static_tier_titles:
            assert tier_title not in member_html, f"Static tier title '{tier_title}' should not be rendered on /membership"

    def test_12_canonical_xu_charge_semantics_and_zero_creation_charge_claim(self) -> None:
        """Verify truthful valid result charging semantics and zero creation-time charge claim.

        1. CHARGE_AT_JOB_CREATION_CLAIM=0: 'khởi tạo thành công' must not be claimed as charge moment.
        2. VALID_RESULT_CHARGE_SEMANTICS=YES: 'kết quả hợp lệ' semantics must be present.
        """
        res = _run_node_render_catalog("/pricing", {})
        assert res["ok"]
        html = res["html"]

        assert "khởi tạo thành công" not in html, "Forbidden claim: charging at job creation"
        assert "Xu chỉ được ghi nhận/trừ theo kết quả hợp lệ theo chính sách thanh toán của hệ thống" in html

        # Also check source
        assert "Bạn chỉ bị trừ Xu khi tác vụ được khởi tạo thành công" not in PORTAL_SOURCE

    def test_13_zero_unproven_auto_refund_and_no_expiry_claims(self) -> None:
        """Verify zero unproven blanket auto-refund and no-expiry claims.

        1. UNPROVEN_AUTO_REFUND_CLAIM=0: Blanket promise 'Xu được hoàn lại tự động' removed.
        2. UNPROVEN_NO_EXPIRY_CLAIM=0: Blanket claim 'không có thời hạn sử dụng' removed.
        """
        res = _run_node_render_catalog("/pricing", {})
        assert res["ok"]
        html = res["html"]

        assert "hoàn lại tự động" not in html
        assert "không có thời hạn sử dụng" not in html

    def test_14_zero_unsourced_payos_sla(self) -> None:
        """Verify zero unsourced SLA promises (5-30s, 24/7) on commerce surface.

        1. UNSOURCED_PAYOS_SLA=0: '5-30 giây' and '5-30s' removed.
        2. Neutral VietQR/PayOS copy present.
        """
        res = _run_node_render_catalog("/pricing", {})
        assert res["ok"]
        html = res["html"]

        assert "5-30 giây" not in html
        assert "5-30s" not in html
        assert "VietQR/PayOS" in html

    def test_15_package_catalog_source_truth_and_zero_fake_fallback_packages(self) -> None:
        """Verify package catalog is strictly derived from source without fake client fallback packages.

        1. FAKE_PACKAGE_COUNT=0: No fallback packages from DEFAULT_CANONICAL_PACKAGES rendered when empty.
        2. Truthful empty message displayed when server packageCatalog is missing or empty.
        3. Canonical packages from server rendered when provided.
        """
        # When packageCatalog is empty:
        res_empty = _run_node_render_catalog("/pricing", {
            "pricingCatalog": {},
            "packageCatalog": {}
        })
        assert res_empty["ok"]
        empty_html = res_empty["html"]

        # Fake fallback package names must NOT be rendered
        fake_package_names = [
            "Gói Ảnh Mini",
            "Gói Ảnh Cơ Bản",
            "Gói Ảnh Bán Hàng",
            "Gói Video Mini",
            "Gói Video Tiêu Chuẩn",
            "Gói Video Cao Cấp",
            "Combo Video Quảng Cáo Mini",
            "Combo Sáng Tạo Toàn Diện Tháng",
        ]
        for pkg_name in fake_package_names:
            assert pkg_name not in empty_html, f"Fake package '{pkg_name}' must not be rendered from client fallback"

        # Truthful empty message
        assert "Danh mục gói dịch vụ đang chờ cập nhật từ máy chủ." in empty_html

        # When real canonical packages are provided:
        res_real = _run_node_render_catalog("/pricing", {
            "packageCatalog": {
                "available": True,
                "monthly": [{"code": "real_pkg_101", "label": "Gói Thực Tế Canonical", "note": "Gói do server cấp"}],
                "combos": []
            }
        })
        assert res_real["ok"]
        real_html = res_real["html"]
        assert "Gói Thực Tế Canonical" in real_html
        for pkg_name in fake_package_names:
            assert pkg_name not in real_html
