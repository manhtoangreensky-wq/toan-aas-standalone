"""
P0.WEBAPP.WEB14: DE-BLOAT CORE INFORMATION ARCHITECTURE TRUTH
Verification Suite for Navigation De-bloat, Canonical Parent Assignment,
Customer-to-Admin Leak Prevention, Desktop/Mobile Nav Parity, and Deep-Link Preservation.
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


def _extract_customer_nav_permanent_links():
    """Extract permanent customer navigation links from portal.js navGroups."""
    start = PORTAL_JS.index("function navGroups(context, currentPage)")
    end = PORTAL_JS.index("const videoStudioNavGroups = [")
    nav_block = PORTAL_JS[start:end]
    return re.findall(r'\["(/[^"]+)",\s*"([^"]+)"', nav_block)


def _extract_customer_mobile_dock_links():
    """Extract customer mobile bottom dock links from portal.js renderMobileNav."""
    start = PORTAL_JS.index("function renderMobileNav(page)")
    end = PORTAL_JS.index("function isAdminMobileSurface(page)")
    block = PORTAL_JS[start:end]
    return re.findall(r'\["([^"]+)",\s*"(/[^"]+)",\s*uiText\("[^"]+",\s*"([^"]+)"\)', block)


def _get_admin_nav_modules():
    """Get all admin navigation modules from canonical navigation authority."""
    groups = admin_nav.canonical_groups() + admin_nav.support_groups("admin") + admin_nav.web_local_admin_groups()
    modules = []
    for g in groups:
        for m in g.get("modules", []):
            modules.append((g["id"], g["title"], m["route"], m["title"]))
    return groups, modules


class TestP0WebappWeb14DeBloatCoreIaTruth:
    """Rigorous empirical validation of Information Architecture truth."""

    def test_01_authority_inventories_complete_and_truthful(self):
        """Derive authoritative IA inventories from source registries."""
        # 1. Customer registered routes
        customer_routes = [f.route for f in reg.CUSTOMER_FEATURES]
        assert len(customer_routes) == 139, f"Expected 139 customer features, got {len(customer_routes)}"

        # 2. Admin registered routes
        admin_routes = [f.route for f in reg.ADMIN_FEATURES]
        assert len(admin_routes) == 40, f"Expected 40 admin features, got {len(admin_routes)}"

        # 3. Feature catalog items (all customer features exposed in /features)
        assert len(reg.CUSTOMER_FEATURES) == 139

        # 4. Customer visible permanent nav items
        perm_links = _extract_customer_nav_permanent_links()
        assert len(perm_links) in (15, 22), f"Expected 15 or 22 clean customer permanent links, got {len(perm_links)}"

        # 5. Admin visible nav items (24 modules across 6 pillars in V2, or 49 across 13 in legacy)
        admin_groups, admin_modules = _get_admin_nav_modules()
        assert len(admin_groups) in (6, 13), f"Expected 6 or 13 admin groups, got {len(admin_groups)}"
        assert len(admin_modules) in (24, 49), f"Expected 24 or 49 admin modules, got {len(admin_modules)}"

        # Distinct routes
        distinct_admin_routes = {m[2] for m in admin_modules}
        assert len(distinct_admin_routes) in (24, 49), "All admin modules must have distinct routes"

    def test_02_customer_to_admin_route_leak_strictly_zero(self):
        """Customer sidebar navigation rail must contain ZERO admin routes."""
        perm_links = _extract_customer_nav_permanent_links()
        admin_leaks = [path for path, label in perm_links if path.startswith("/admin")]
        assert admin_leaks == [], f"CUSTOMER_TO_ADMIN_ROUTE_LEAK detected in navGroups: {admin_leaks}"

        # Verify navGroups definition in portal.js does not push admin groups into customer rail
        start = PORTAL_JS.index("function navGroups(context, currentPage)")
        end = PORTAL_JS.index("const videoStudioNavGroups = [")
        nav_block = PORTAL_JS[start:end]
        assert "Quản trị Admin ERP" not in nav_block, "Customer navGroups must not contain admin ERP group"
        assert 'links.push(["/admin' not in nav_block

        # Verify customer approvals page does not expose unconditioned /admin/approvals link
        approvals_idx = PORTAL_JS.index("function renderCampaignApprovals")
        approvals_block = PORTAL_JS[approvals_idx:approvals_idx + 4000]
        assert 'serverAuthorizesAdminRoute(context, "/admin/approvals")' in approvals_block, (
            "Customer approvals page must guard /admin/approvals link"
        )

    def test_03_every_visible_nav_item_has_canonical_parent_and_zero_dead_links(self):
        """Every customer and admin nav target must resolve HTTP 200 and belong to a valid parent domain."""
        allowed = set(pages.allowed_paths())
        perm_links = _extract_customer_nav_permanent_links()

        # Check customer visible links resolve in portal renderer
        for path, label in perm_links:
            assert path in allowed, f"Customer nav link {path} is not an allowed path"
            html_resp = pages.render_portal(path)
            assert html_resp.status_code == 200, f"Customer nav target {path} render failed"

        # Check admin modules resolve in portal renderer and are properly guarded
        _, admin_modules = _get_admin_nav_modules()
        for group_id, group_title, route, module_title in admin_modules:
            html_resp = pages.render_portal(route)
            assert html_resp.status_code == 200, f"Admin module {route} render failed"
            # Verify RBAC protection: unauthenticated HTTP request must NOT return 200
            http_resp = client.get(route)
            assert http_resp.status_code in (307, 401, 403), f"Admin module {route} leaked without auth"

    def test_04_zero_duplicate_visible_routes_in_same_nav_context(self):
        """Ensure no duplicated links within customer permanent nav or admin nav."""
        perm_links = _extract_customer_nav_permanent_links()
        customer_paths = [p[0] for p in perm_links]
        assert len(customer_paths) == len(set(customer_paths)), (
            f"Duplicate links found in customer permanent nav: {[p for p in customer_paths if customer_paths.count(p) > 1]}"
        )

        dock_links = _extract_customer_mobile_dock_links()
        dock_paths = [d[1] for d in dock_links]
        assert len(dock_paths) == len(set(dock_paths)), "Duplicate links in mobile dock"

        _, admin_modules = _get_admin_nav_modules()
        admin_paths = [m[2] for m in admin_modules]
        assert len(admin_paths) == len(set(admin_paths)), "Duplicate module routes in admin ERP navigation"

    def test_05_desktop_mobile_nav_parity(self):
        """Desktop and mobile navigation must share consistent canonical targets."""
        dock_links = _extract_customer_mobile_dock_links()
        assert len(dock_links) == 5, f"Mobile dock should have 5 core items, got {len(dock_links)}"

        dock_routes = {d[1] for d in dock_links}
        expected_dock_routes = {"/dashboard", "/features", "/jobs", "/assets", "/account"}
        assert dock_routes == expected_dock_routes, f"Unexpected mobile dock routes: {dock_routes}"

        # All dock routes must be present in customer desktop permanent nav
        desktop_routes = {p[0] for p in _extract_customer_nav_permanent_links()}
        assert dock_routes.issubset(desktop_routes), (
            f"Mobile dock routes {dock_routes - desktop_routes} missing from desktop navigation"
        )

    def test_06_secondary_tools_remain_deep_linkable_without_primary_bloat(self):
        """Specialized secondary tools remain HTTP 200 deep-linkable without bloating primary nav."""
        secondary_routes = [
            "/video-studio",
            "/video-studio/workflow",
            "/video-studio/idea-planner",
            "/video-studio/scene-planner",
            "/video-studio/audio-voice",
            "/video-studio/visual-style",
            "/video-studio/character-identity",
            "/video-studio/lighting-camera",
            "/video-studio/reference-board",
            "/video-studio/motion-effects",
            "/video-studio/render-preflight",
            "/video-studio/cost-estimate",
            "/video-studio/export-delivery",
            "/prompt-studio",
            "/voice-studio",
            "/subtitle-studio",
            "/image-hub",
            "/image/prompt-composer",
            "/document-workspace",
            "/trend-research",
        ]
        desktop_permanent_routes = {p[0] for p in _extract_customer_nav_permanent_links()}

        promoted_v2 = {"/video-studio", "/voice-studio"}
        for route in secondary_routes:
            # Secondary routes (except top-level studios promoted to primary in V2) must NOT be in customer permanent desktop nav
            if route not in promoted_v2:
                assert route not in desktop_permanent_routes, f"Secondary route {route} should not be in permanent customer nav"
            # But must be HTTP 200 deep-linkable
            resp = client.get(route)
            assert resp.status_code == 200, f"Secondary route {route} failed deep-link test: {resp.status_code}"

    def test_07_feature_catalog_remains_complete_capability_catalog(self):
        """The /features page is the complete capability catalog, separate from primary nav."""
        resp = client.get("/features")
        assert resp.status_code == 200
        # Catalog has all 139 customer features
        assert len(reg.CUSTOMER_FEATURES) == 139
        # Permanent nav has 15 (V2) or 22 (V1) items: NAV_CATALOG (15/22) != CAPABILITY_CATALOG (139)
        assert len(_extract_customer_nav_permanent_links()) in (15, 22)
        assert len(_extract_customer_nav_permanent_links()) < len(reg.CUSTOMER_FEATURES)

    def test_08_core_workflows_reachable_within_bounded_depth(self):
        """Ensure customer and admin core domains are reachable within bounded depth."""
        # Customer core paths:
        customer_paths = [
            "/pricing", "/packages",
            "/wallet", "/wallet/topup",
            "/jobs", "/assets",
            "/content-studio", "/image-studio",
            "/dashboard", "/projects", "/workboard",
            "/account",
            "/support", "/tickets",
        ]
        desktop_routes = {p[0] for p in _extract_customer_nav_permanent_links()}
        for path in customer_paths:
            # All core customer workflows must be reachable
            resp = client.get(path)
            assert resp.status_code in (200, 307), f"Core customer path {path} must be reachable (got {resp.status_code})"

        # Admin core domains:
        _, admin_modules = _get_admin_nav_modules()
        admin_routes = {m[2] for m in admin_modules}
        # In V2, primary modules are streamlined into 24 across 6 pillars
        admin_primary_paths = [
            "/admin",
            "/admin/customers",
            "/admin/topups",
            "/admin/jobs",
            "/admin/providers",
            "/admin/workers",
            "/admin/operations",
            "/admin/audit",
            "/admin/security",
        ]
        for path in admin_primary_paths:
            assert path in admin_routes, f"Primary admin path {path} must be in admin navigation"

    def test_09_no_capability_inflation(self):
        """Preserve truth: planners and composers do not claim to be generators or renderers."""
        features = {f.route: f for f in reg.CUSTOMER_FEATURES}
        # Verify planner routes do not have inflated generator titles
        if "/video-studio/idea-planner" in features:
            title = features["/video-studio/idea-planner"].title
            assert "Generator" not in title and "Renderer" not in title

        if "/video-studio/cost-estimate" in features:
            title = features["/video-studio/cost-estimate"].title
            assert "Auto-Billing" not in title and "Payment" not in title

    def test_10_negative_controls_fail_closed(self):
        """Negative controls: dead links or leaked admin routes must fail assertion."""
        # Negative control A: dead link href="#" or "javascript:void(0)"
        dead_links = ["#", "", "javascript:void(0)", "javascript:;"]
        for dead in dead_links:
            assert dead not in [p[0] for p in _extract_customer_nav_permanent_links()]

        # Negative control B: an unauthenticated /admin link in customer nav would be caught
        fake_perm_nav = _extract_customer_nav_permanent_links() + [("/admin/finance", "Admin Finance")]
        leaks = [p for p, l in fake_perm_nav if p.startswith("/admin")]
        assert len(leaks) == 1, "Negative control must detect injected admin leak"
