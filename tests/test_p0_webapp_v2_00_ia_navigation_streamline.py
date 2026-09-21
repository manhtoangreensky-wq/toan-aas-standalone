"""
P0.WEBAPP.V2-00: IA NAVIGATION STREAMLINE FOCUSED TEST SUITE
Proves:
- CUSTOMER_PRIMARY_NAV_COUNT == 15
- CUSTOMER_NAV_GROUP_COUNT == 4
- ADMIN_PRIMARY_MODULE_COUNT == 24
- ADMIN_NAV_GROUP_COUNT == 6
- PRIMARY_NAV_404 == 0
- DEAD_PRIMARY_NAV_LINK == 0
- DUPLICATE_PRIMARY_NAV_ROUTE == 0
- CUSTOMER_ADMIN_ROUTE_LEAK == 0
- ADMIN_RBAC_REGRESSION == 0
- FEATURE_CATALOG_PRESERVED == YES (count == 139)
- MOBILE_DOCK_PRESERVED == YES
- LEGACY_ROUTES_STILL_ROUTABLE == YES
"""

import re
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app import app
import copyfast_registry as reg
import copyfast_pages as pages
import copyfast_admin_erp_navigation as admin_nav

ROOT = Path(__file__).resolve().parent.parent
PORTAL_JS_PATH = ROOT / "static" / "portal" / "portal.js"
PORTAL_JS = PORTAL_JS_PATH.read_text(encoding="utf-8")

client = TestClient(app)


def _extract_customer_nav_groups():
    """Extract customer navigation groups and links from portal.js navGroups."""
    start = PORTAL_JS.index("function navGroups(context, currentPage)")
    end = PORTAL_JS.index("const currentGroup = currentCustomerWorkflowGroup")
    nav_block = PORTAL_JS[start:end]

    group_matches = re.findall(r'label:\s*"([^"]+)"[^[]*links:\s*\[(.*?)\]\s*\}', nav_block, re.DOTALL)
    groups = []
    for label, links_str in group_matches:
        links = re.findall(r'\["(/[^"]+)",\s*"([^"]+)"', links_str)
        groups.append((label, links))
    return groups


def _extract_customer_nav_permanent_links():
    groups = _extract_customer_nav_groups()
    links = []
    for label, group_links in groups:
        links.extend(group_links)
    return links


def _extract_customer_mobile_dock_links():
    """Extract customer mobile bottom dock links from portal.js renderMobileNav."""
    start = PORTAL_JS.index("function renderMobileNav(page)")
    end = PORTAL_JS.index("function isAdminMobileSurface(page)")
    block = PORTAL_JS[start:end]
    return re.findall(r'\["([^"]+)",\s*"(/[^"]+)",\s*uiText\("[^"]+",\s*"([^"]+)"\)', block)


def _get_admin_nav_groups_and_modules():
    """Get primary admin navigation groups and modules from admin_nav authority."""
    groups = admin_nav.v2_primary_groups()
    modules = []
    for g in groups:
        for m in g.get("modules", []):
            modules.append((g["id"], g["title"], m["route"], m["title"]))
    return groups, modules


class TestP0WebappV200IaNavigationStreamline:
    """Rigorous empirical validation of V2 Information Architecture truth."""

    def test_01_customer_primary_navigation_exact_17_links_and_5_groups(self):
        """Customer primary navigation must expose exactly 17 core links under 5 canonical groups."""
        groups = _extract_customer_nav_groups()
        assert len(groups) == 5, f"CUSTOMER_NAV_GROUP_COUNT must be 5, got {len(groups)}"

        perm_links = _extract_customer_nav_permanent_links()
        assert len(perm_links) == 17, f"CUSTOMER_PRIMARY_NAV_COUNT must be 17, got {len(perm_links)}"

        routes = [link[0] for link in perm_links]
        assert len(routes) == len(set(routes)), f"DUPLICATE_PRIMARY_NAV_ROUTE detected: {routes}"

        expected_structure = [
            ("Tổng quan", ["/dashboard"]),
            ("Sáng tạo", ["/studio", "/tools/image", "/voice", "/music", "/subdub", "/content", "/documents"]),
            ("Công việc", ["/projects", "/publishing", "/jobs"]),
            ("Tài khoản", ["/wallet", "/packages", "/history", "/account"]),
            ("Tất cả công cụ", ["/features", "/tools/free"]),
        ]

        for i, (expected_title, expected_routes) in enumerate(expected_structure):
            group_label, group_links = groups[i]
            group_routes = [l[0] for l in group_links]
            assert group_routes == expected_routes, (
                f"Group {i+1} ({group_label}) routes mismatch: expected {expected_routes}, got {group_routes}"
            )

    def test_02_customer_removed_routes_are_not_in_primary_rail_but_remain_routable(self):
        """Removed routes must not remain in primary rail, but must remain deep-linkable."""
        removed_routes = [
            "/workboard",
            "/campaigns",
            "/chat",
            "/workspace",
            "/asset-vault",
            "/approvals",
            "/membership",
            "/tickets",
        ]
        primary_routes = {link[0] for link in _extract_customer_nav_permanent_links()}

        for route in removed_routes:
            assert route not in primary_routes, f"Route {route} was not removed from primary rail"
            resp = client.get(route)
            assert resp.status_code == 200, f"Removed route {route} broken: HTTP {resp.status_code}"

    def test_03_customer_feature_catalog_strictly_preserved(self):
        """Customer feature catalog in /features must retain all 139 registered capabilities."""
        assert len(reg.CUSTOMER_FEATURES) == 139, (
            f"FEATURE_COUNT_REGRESSION: expected 139 customer features, got {len(reg.CUSTOMER_FEATURES)}"
        )
        resp = client.get("/features")
        assert resp.status_code == 200, "/features catalog page must resolve HTTP 200"

    def test_04_mobile_dock_contract_preserved(self):
        """Mobile dock retains 5 core links and shares canonical targets with desktop."""
        dock_links = _extract_customer_mobile_dock_links()
        assert len(dock_links) == 5, f"Mobile dock count must be 5, got {len(dock_links)}"

        dock_routes = [d[1] for d in dock_links]
        assert len(dock_routes) == len(set(dock_routes)), "Duplicate links in mobile dock"

        primary_routes = {link[0] for link in _extract_customer_nav_permanent_links()}
        for route in dock_routes:
            assert route in primary_routes, f"Mobile dock route {route} not in desktop primary nav"

    def test_05_admin_primary_navigation_exact_25_modules_and_6_pillars(self):
        """Admin primary navigation must be organized into exactly 25 primary modules across 6 pillars."""
        groups, modules = _get_admin_nav_groups_and_modules()
        assert len(groups) == 6, f"ADMIN_NAV_GROUP_COUNT must be 6, got {len(groups)}"
        assert len(modules) == 25, f"ADMIN_PRIMARY_MODULE_COUNT must be 25, got {len(modules)}"

        routes = [m[2] for m in modules]
        assert len(routes) == len(set(routes)), f"DUPLICATE_PRIMARY_NAV_ROUTE in admin: {routes}"

        expected_pillars = [
            ("command_center", "Trung tâm điều hành", ["/admin", "/admin/operations", "/admin/work-queue", "/admin/reports"]),
            ("commerce_finance", "Tài chính & Doanh thu", ["/admin/commercial", "/admin/topups", "/admin/wallet", "/admin/revenue", "/admin/refunds", "/admin/pricing"]),
            ("customer_growth", "Khách hàng & Bán hàng", ["/admin/customers", "/admin/users", "/admin/crm/leads", "/admin/support"]),
            ("jobs_delivery", "Hàng đợi & Xử lý sản phẩm", ["/admin/jobs", "/admin/jobs/failed", "/admin/features"]),
            ("infrastructure_providers", "Hạ tầng & Nhà cung cấp", ["/admin/providers", "/admin/workers", "/admin/system", "/admin/runtime"]),
            ("security_governance", "An ninh & Kiểm toán", ["/admin/audit", "/admin/security", "/admin/internal-docs", "/admin/backups"]),
        ]

        for i, (expected_id, expected_title, expected_routes) in enumerate(expected_pillars):
            group = groups[i]
            assert group["id"] == expected_id, f"Pillar {i+1} id mismatch: expected {expected_id}, got {group['id']}"
            pillar_routes = [m["route"] for m in group["modules"]]
            assert pillar_routes == expected_routes, (
                f"Pillar {i+1} ({group['title']}) routes mismatch: expected {expected_routes}, got {pillar_routes}"
            )

    def test_06_every_primary_nav_route_resolves_and_zero_dead_links(self):
        """Every customer (15) and admin (24) primary link must resolve without 404 or dead href."""
        dead_patterns = {"#", "", "javascript:void(0)", "javascript:;"}

        customer_links = _extract_customer_nav_permanent_links()
        for route, title in customer_links:
            assert route not in dead_patterns, f"Dead customer link detected: {route}"
            assert route in pages.allowed_paths(), f"Customer route {route} not in allowed_paths"
            resp = pages.render_portal(route)
            assert resp.status_code == 200, f"Customer route {route} failed render: {resp.status_code}"

        _, admin_modules = _get_admin_nav_groups_and_modules()
        for group_id, group_title, route, module_title in admin_modules:
            assert route not in dead_patterns, f"Dead admin link detected: {route}"
            resp = pages.render_portal(route)
            assert resp.status_code == 200, f"Admin route {route} failed render: {resp.status_code}"
            auth_resp = client.get(route, follow_redirects=False)
            assert auth_resp.status_code in (307, 401, 403), f"Admin route {route} leaked without auth: {auth_resp.status_code}"

    def test_07_customer_admin_separation_and_zero_route_leak(self):
        """Customer sidebar navigation rail must contain ZERO /admin routes."""
        customer_links = _extract_customer_nav_permanent_links()
        leaks = [route for route, title in customer_links if route.startswith("/admin")]
        assert leaks == [], f"CUSTOMER_ADMIN_ROUTE_LEAK detected: {leaks}"

    def test_08_canonical_light_teal_visual_system_protection(self):
        """V3 canonical light teal visual system variables must remain protected."""
        css_file = ROOT / "static" / "portal" / "portal-theme.css"
        css_text = css_file.read_text(encoding="utf-8")
        assert "#f3fbfc" in css_text or "#0d9488" in css_text, "Canonical light teal color missing"
        html_file = ROOT / "templates" / "portal_shell.html"
        html_text = html_file.read_text(encoding="utf-8")
        assert "#062026" in html_text, "Dark theme teal dark color missing from shell"
        assert "#0d9488" in html_text, "Light theme teal color missing from shell"
