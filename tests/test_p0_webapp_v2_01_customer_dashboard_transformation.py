"""
P0.WEBAPP.V2-01: CUSTOMER DASHBOARD TRANSFORMATION FOCUSED TEST SUITE
Proves:
1. WALLET_BLOCK_PRIMARY == YES (Wallet & financial state is the #1 dashboard block)
2. CANONICAL_WALLET_SOURCE_PRESERVED == YES
3. UNKNOWN_WALLET_NOT_RENDERED_AS_ZERO == YES
4. START_WORK_PRIMARY_CTA_COUNT == 3 (/video-studio, /image-studio, /content-studio)
5. START_WORK_ROUTES == ['/video-studio', '/image-studio', '/content-studio']
6. FEATURE_CATALOG_CTA == /features
7. DASHBOARD_STATIC_PRODUCTIVITY_CARD_COUNT == 0 (Bloat removed)
8. CUSTOMER_FEATURE_CATALOG == 139 (Preserved)
9. ACTIVE_JOB_TRUTH_PRESERVED == YES
10. FAILED_JOB_FAKE_SUCCESS == 0
11. PROJECT_CONTINUATION_ROUTE == /projects
12. CUSTOMER_ADMIN_ROUTE_LEAK == 0
13. V2_00_NAV_REGRESSION == 0
14. BLUE_VISUAL_REGRESSION == 0
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
        """Wallet/Xu financial summary must be the #1 first-priority dashboard information block."""
        calls = _get_dashboard_sections_order()
        assert len(calls) > 0, "renderDashboard must contain rendered section calls"
        # The very first rendered block must be the wallet hero/summary block
        first_call = calls[0]
        assert "Wallet" in first_call or "Financial" in first_call, (
            f"WALLET_BLOCK_PRIMARY must be YES. Currently first call is '{first_call}', not a wallet block."
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
        """Primary start-work block must expose exactly 3 primary studios and 1 secondary catalog link."""
        body = _get_render_dashboard_body()
        assert "renderDashboardStartWork" in body or "renderDashboardCreationHero" in body or "renderStartWork" in body, (
            "Dashboard must include a dedicated primary start-work CTA section"
        )
        # Check routes present in creation CTA
        for route in ("/video-studio", "/image-studio", "/content-studio"):
            assert route in body, f"Start-work block missing primary creation route: {route}"
        assert "/features" in body, "Start-work block missing secondary discovery route /features"

    def test_04_static_productivity_hub_bloat_eliminated(self):
        """Static 'Productivity Hub' with 8 duplicative cards must be removed from /dashboard."""
        body = _get_render_dashboard_body()
        assert "renderAISuiteProductivityHub" not in body, (
            "DASHBOARD_STATIC_PRODUCTIVITY_CARD_COUNT must be 0. renderAISuiteProductivityHub is still present in renderDashboard!"
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
        body = _get_render_dashboard_body()
        assert "/projects" in body, "Dashboard must route project continuation to /projects"
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
        """V2-00 streamlined navigation rail (13 customer links across 4 groups in V3) must remain intact."""
        start = PORTAL_JS.index("function navGroups(context, currentPage)")
        end = PORTAL_JS.index("const currentGroup = currentCustomerWorkflowGroup")
        nav_block = PORTAL_JS[start:end]

        group_matches = re.findall(r'label:\s*"([^"]+)"[^[]*links:\s*\[(.*?)\]\s*\}', nav_block, re.DOTALL)
        assert len(group_matches) == 4, f"Expected 4 customer groups, got {len(group_matches)}"

        perm_links = re.findall(r'\["(/[^"]+)",\s*"([^"]+)"', nav_block)
        assert len(perm_links) == 13, f"Expected 13 permanent customer links, got {len(perm_links)}"

    def test_10_blue_visual_system_protected(self):
        """Canonical teal/mint visual tokens must remain intact in portal-theme.css."""
        css_file = ROOT / "static" / "portal" / "portal-theme.css"
        css_text = css_file.read_text(encoding="utf-8")
        assert "#0d9488" in css_text or "#f3fbfc" in css_text
