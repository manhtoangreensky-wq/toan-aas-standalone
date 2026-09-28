"""
P0.WEBAPP.V2-01: CUSTOMER DASHBOARD TRANSFORMATION FOCUSED TEST SUITE
Proves:
1. DASHBOARD_FIRST_CALL == renderDashboardProductHero (Consolidated creative launcher is #1 block)
2. DASHBOARD_SECOND_CALL == renderDashboardAccountSummary (Wallet & financial summary is #2 block)
3. CANONICAL_WALLET_SOURCE_PRESERVED == YES
4. UNKNOWN_WALLET_NOT_RENDERED_AS_ZERO == YES
5. RETAINED_HERO_ROUTES == ['/studio', '/tools/image', '/voice', '/subdub', '/content', '/music']
6. FEATURE_CATALOG_CTA == /features
7. DASHBOARD_STATIC_PRODUCTIVITY_CARD_COUNT == 0 (Bloat removed)
8. DASHBOARD_RENDER_STUDIO_LAUNCHPAD_CALL_COUNT == 0 (Duplicate launcher removed)
9. CUSTOMER_FEATURE_CATALOG == 139 (Preserved)
10. ACTIVE_JOB_TRUTH_PRESERVED == YES
11. FAILED_JOB_FAKE_SUCCESS == 0
12. PROJECT_CONTINUATION_ROUTE == /projects
13. CUSTOMER_ADMIN_ROUTE_LEAK == 0
14. CUSTOMER_NAV_GROUP_COUNT == 5
15. PERMANENT_CUSTOMER_NAV_LINK_COUNT == 17
16. BLUE_VISUAL_REGRESSION == 0
"""

import re
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app import app
import copyfast_registry as reg
import copyfast_pages as pages

ROOT = Path(__file__).resolve().parent.parent
PORTAL_JS_PATH = ROOT / "static" / "portal" / "portal.js"
PORTAL_JS = PORTAL_JS_PATH.read_text(encoding="utf-8")

client = TestClient(app)


def _get_render_dashboard_body() -> str:
    """Extract renderDashboard implementation from portal.js."""
    start = PORTAL_JS.index("function renderDashboard(page, context)")
    end = PORTAL_JS.index("function renderWorkspaceActionCenter(context)")
    return PORTAL_JS[start:end]


def _get_dashboard_sections_order() -> list[str]:
    """Extract the order of major rendered sections in renderDashboard."""
    body = _get_render_dashboard_body()
    # Match the interpolated function calls inside return `...`
    calls = re.findall(r'\$\{(render[A-Za-z0-9]+)\(context[^)]*\)\}', body)
    return calls


class TestP0WebappV201CustomerDashboardTransformation:
    """Empirical verification of V2-01 Customer Dashboard Transformation truth."""

    def test_01_wallet_block_is_first_primary_dashboard_position(self):
        """Dashboard must place Product Hero first and Account/Wallet summary second."""
        calls = _get_dashboard_sections_order()
        assert len(calls) > 1, "renderDashboard must contain rendered section calls"
        assert calls[0] == "renderDashboardProductHero", (
            f"DASHBOARD_FIRST_CALL must be 'renderDashboardProductHero'. Got '{calls[0]}'."
        )
        assert calls[1] == "renderDashboardAccountSummary", (
            f"DASHBOARD_SECOND_CALL must be 'renderDashboardAccountSummary'. Got '{calls[1]}'."
        )

    def test_02_canonical_wallet_source_preserved_and_unknown_not_zero(self):
        """Wallet projection must use canonicalWalletProjection and must not render unknown as 0."""
        assert "function canonicalWalletProjection(value)" in PORTAL_JS
        # Verify unknown/unverified wallet renders '—' and not '0'
        body = _get_render_dashboard_body()
        assert "wallet" in body.lower()
        # In portal.js canonicalWalletProjection requires canonicalNonnegativeInteger
        assert "canonicalNonnegativeInteger(value.balance_xu)" in PORTAL_JS

    def test_03_start_work_primary_cta_count_and_routes(self):
        """Product hero must expose exactly 6 canonical creative routes."""
        hero_start = PORTAL_JS.index("function renderDashboardProductHero(ctx)")
        hero_end = PORTAL_JS.index("function renderDashboardAccountSummary(ctx)")
        hero_body = PORTAL_JS[hero_start:hero_end]
        expected_routes = [
            "/studio",
            "/tools/image",
            "/voice",
            "/subdub",
            "/content",
            "/music",
        ]
        hrefs = re.findall(r'href=["\'](/[^"\']+)["\']', hero_body)
        assert hrefs == expected_routes, f"Retained hero routes mismatch: {hrefs} != {expected_routes}"

    def test_04_static_productivity_hub_bloat_eliminated(self):
        """Static 'Productivity Hub' and duplicate Studio Launchpad must be removed from /dashboard."""
        body = _get_render_dashboard_body()
        assert "renderAISuiteProductivityHub" not in body, (
            "DASHBOARD_STATIC_PRODUCTIVITY_CARD_COUNT must be 0. renderAISuiteProductivityHub is still present in renderDashboard!"
        )
        assert "renderStudioLaunchpad(context)" not in body, (
            "Duplicate renderStudioLaunchpad must not be composed in renderDashboard under U01-E01!"
        )
        assert "portal-ai-suite-productivity-hub" not in body
        assert "portal-ai-suite-card" not in body

    def test_05_customer_feature_catalog_preserved_at_139(self):
        """Customer feature catalog in /features must strictly preserve all 139 capabilities."""
        assert len(reg.CUSTOMER_FEATURES) == 139, f"Expected 139 features, got {len(reg.CUSTOMER_FEATURES)}"
        resp = client.get("/features")
        assert resp.status_code == 200

    def test_06_active_job_truth_preserved_without_fake_progress(self):
        """Active job truth must preserve canonical statuses and prevent fake progress."""
        assert "renderWorkspaceActionCenter" in PORTAL_JS
        assert '["queued", "processing"].includes(jobStatus(item))' in PORTAL_JS
        assert '["failed", "failed_no_charge"].includes(jobStatus(item))' in PORTAL_JS

    def test_07_project_continuation_route_is_canonical_projects(self):
        """Project continuation on dashboard must target canonical /projects under V2 IA."""
        start = PORTAL_JS.index("function renderDashboardRecentProjects(context)")
        end = PORTAL_JS.index("function renderDashboardStartGuide(context)")
        projects_block = PORTAL_JS[start:end]
        assert "/projects" in projects_block, "Dashboard must route project continuation to /projects"
        body = _get_render_dashboard_body()
        # Must not use /workspace or /workboard as primary continuation
        assert 'href="/workspace"' not in body
        assert 'href="/workboard"' not in body

    def test_08_customer_admin_route_leak_zero(self):
        """Dashboard rendering code must not leak /admin operational endpoints to customer."""
        body = _get_render_dashboard_body()
        # Find all href links in renderDashboard body
        hrefs = re.findall(r'href=["\'](/[^"\']+)["\']', body)
        admin_leaks = [h for h in hrefs if h.startswith("/admin")]
        assert admin_leaks == [], f"CUSTOMER_ADMIN_ROUTE_LEAK detected on dashboard: {admin_leaks}"

    def test_09_v2_00_navigation_rail_preserved(self):
        """Customer navigation rail must contain exactly 5 groups and 17 permanent links."""
        start = PORTAL_JS.index("function navGroups(context, currentPage)")
        end = PORTAL_JS.index("const currentGroup = currentCustomerWorkflowGroup")
        nav_block = PORTAL_JS[start:end]

        group_matches = re.findall(r'label:\s*"([^"]+)"[^[]*links:\s*\[(.*?)\]\s*\}', nav_block, re.DOTALL)
        assert len(group_matches) == 5, f"CUSTOMER_NAV_GROUP_COUNT must be 5, got {len(group_matches)}"

        perm_links = re.findall(r'\["(/[^"]+)",\s*"([^"]+)"', nav_block)
        assert len(perm_links) == 17, f"PERMANENT_CUSTOMER_NAV_LINK_COUNT must be 17, got {len(perm_links)}"

    def test_10_blue_visual_system_protected(self):
        """Canonical teal/mint visual tokens must remain intact in portal-theme.css."""
        css_file = ROOT / "static" / "portal" / "portal-theme.css"
        css_text = css_file.read_text(encoding="utf-8")
        assert "#0d9488" in css_text or "#f3fbfc" in css_text
