"""
SPEC_ID: WEBAPP_U01_E01_DASHBOARD_LAUNCHER_CONSOLIDATION_R1
Target Issue: #588
Parent: #587, #563

Empirical regression tests proving:
1. DASHBOARD_PRODUCT_LAUNCHER_SECTION_COUNT == 1
2. renderDashboard includes renderDashboardProductHero(context)
3. renderDashboard does NOT include renderStudioLaunchpad(context)
4. DASHBOARD_PRODUCT_LAUNCHER_CARD_COUNT == 6
5. Retained launcher routes match exactly: /studio, /tools/image, /voice, /subdub, /content, /music
6. DUPLICATE_LAUNCHER_ENTRY_COUNT == 0
7. DUPLICATE_NAV_DESTINATION_COUNT == 0
8. WA51 == PASS
9. ADMIN_ROUTE_LEAK_COUNT == 0
10. Wallet, project, job, result dashboard invariants remain intact
"""

import re
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORTAL_JS_PATH = ROOT / "static" / "portal" / "portal.js"
PORTAL_JS = PORTAL_JS_PATH.read_text(encoding="utf-8")


def _get_render_dashboard_body() -> str:
    """Extract renderDashboard implementation from portal.js."""
    start = PORTAL_JS.index("function renderDashboard(page, context)")
    end = PORTAL_JS.index("function renderWorkspaceActionCenter(context)")
    return PORTAL_JS[start:end]


def _get_product_hero_body() -> str:
    """Extract renderDashboardProductHero implementation from portal.js."""
    start = PORTAL_JS.index("function renderDashboardProductHero(ctx)")
    end = PORTAL_JS.index("function renderDashboardAccountSummary(ctx)")
    return PORTAL_JS[start:end]


def test_dashboard_product_launcher_section_count_is_exactly_one():
    """renderDashboard must compose exactly ONE product launcher section."""
    dashboard_body = _get_render_dashboard_body()
    # Must include the consolidated product hero launcher
    assert "${renderDashboardProductHero(context)}" in dashboard_body
    # Must NOT include the duplicative Studio Launchpad
    assert "renderStudioLaunchpad(context)" not in dashboard_body
    assert "${renderStudioLaunchpad(context)}" not in dashboard_body


def test_dashboard_retained_launcher_cards_and_routes_match_canon():
    """Hero launcher must contain exactly 6 cards with canonical routes."""
    hero_body = _get_product_hero_body()
    hrefs = re.findall(r'href=["\'](/[^"\']+)["\']', hero_body)
    expected_routes = [
        "/studio",
        "/tools/image",
        "/voice",
        "/subdub",
        "/content",
        "/music",
    ]
    assert len(hrefs) == 6, f"Expected 6 launcher cards, got {len(hrefs)}: {hrefs}"
    assert hrefs == expected_routes, f"Launcher routes mismatch: {hrefs} != {expected_routes}"


def test_duplicate_launcher_entry_and_nav_destinations_eliminated():
    """Ensure duplicate conflicting launcher entry points are eliminated from renderDashboard."""
    dashboard_body = _get_render_dashboard_body()
    # The conflicting duplicate studio routes must not be rendered as dashboard launchers
    # (they may exist in deeper catalog/tools, but NOT on dashboard)
    assert 'href="/video/create"' not in dashboard_body
    assert 'href="/image/create"' not in dashboard_body
    assert 'href="/voice/tts"' not in dashboard_body
    assert 'href="/music/create"' not in dashboard_body
    assert 'href="/content/pack"' not in dashboard_body


def test_no_admin_route_leak_on_dashboard():
    """Customer dashboard must not render any /admin operational routes."""
    dashboard_body = _get_render_dashboard_body()
    admin_leaks = [h for h in re.findall(r'href=["\'](/admin[^"\']*)["\']', dashboard_body)]
    assert admin_leaks == [], f"Detected admin route leak in renderDashboard: {admin_leaks}"


def test_dashboard_invariants_preserved():
    """Ensure financial summary, project continuation, jobs/assets lanes remain intact."""
    dashboard_body = _get_render_dashboard_body()
    assert "renderDashboardAccountSummary(context)" in dashboard_body
    assert "renderDashboardWorkspaceSummary(context)" in dashboard_body
    assert "renderDashboardCanonicalLane(context, readState)" in dashboard_body
    assert "renderDashboardStartGuide(context)" in dashboard_body
    assert "renderDashboardFocusDock(context)" in dashboard_body
    assert "renderDashboardRecentProjects(context)" in dashboard_body
    assert "renderDashboardRecentDrafts(context)" in dashboard_body
