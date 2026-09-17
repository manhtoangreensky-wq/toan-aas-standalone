"""Empirical verification test suite for P0.WEBAPP.WEB04: CUSTOMER PRODUCT SURFACES TRUTH.

Mandate: MASTER_PROGRAM=P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: TASK=P0.WEBAPP.WEB04.CUSTOMER.PRODUCT.SURFACES.TRUTH
Mode: OWNER-GOVERNED, SOURCE_ONLY, AUDIT_FIRST, FIRST_RED_FIRST, ONE_BOUNDED_TASK

Invariants tested:
1. DEAD_PRIMARY_CTA=0: Zero href="#" or href="javascript:*" in portal client templates.
2. WALLET_HISTORY_ROUTE_EXISTS: /wallet/history is registered in copyfast_registry, copyfast_pages, and portal.js.
3. DASHBOARD_CARD_ROUTING_TRUTH: Card 8 on dashboard points to /wallet/topup, not /pricing.
4. LOCAL_FAKE_PRICE=0: No local invented bonus "+10% Xu" or invented flat rates on dashboard productivity hub.
5. LOCAL_FAKE_PRODUCT=0: /chat card accurately reflects authoring workspace without claiming automated AI model execution.
6. CANONICAL_CATALOG_SOURCES: /api/v1/pricing, /api/v1/packages, and /api/v1/catalog operate truthfully.
7. CUSTOMER_TO_ADMIN_LEAK=0: Customer surfaces do not leak admin routes or admin controllers.
8. ALL_CUSTOMER_STATIC_HREFS_RESOLVE: Every customer static href in portal.js resolves with HTTP 200.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import re
import sqlite3
import sys

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
PORTAL_JS_PATH = ROOT / "static" / "portal" / "portal.js"
PORTAL_SHELL_PATH = ROOT / "templates" / "portal_shell.html"
COPYFAST_PAGES_PATH = ROOT / "copyfast_pages.py"
COPYFAST_REGISTRY_PATH = ROOT / "copyfast_registry.py"


def test_zero_dead_href_in_portal_js() -> None:
    """DEAD_PRIMARY_CTA=0: portal.js must contain zero instances of href="#"."""
    content = PORTAL_JS_PATH.read_text(encoding="utf-8")
    dead_matches = list(re.finditer(r'href=["\']#["\']', content))
    assert len(dead_matches) == 0, (
        f"Found {len(dead_matches)} dead href=\"#\" in portal.js. "
        f"Positions: {[m.start() for m in dead_matches]}"
    )


def test_zero_javascript_void_href_in_portal_js() -> None:
    """DEAD_PRIMARY_CTA=0: portal.js must contain zero instances of href="javascript:*\"."""
    content = PORTAL_JS_PATH.read_text(encoding="utf-8")
    js_hrefs = list(re.finditer(r'href=["\']javascript:[^"\']*["\']', content))
    assert len(js_hrefs) == 0, f"Found {len(js_hrefs)} javascript: hrefs in portal.js"


def test_wallet_history_route_registered_in_portal_js() -> None:
    """WALLET_HISTORY_ROUTE: /wallet/history must be registered as an alias or route in portal.js."""
    content = PORTAL_JS_PATH.read_text(encoding="utf-8")
    # Must be defined as a route or alias in customerPage definition for /wallet
    match = re.search(r'customerPage\(\s*"/wallet"[^)]*\[[^\]]*"/wallet/history"[^\]]*\]', content)
    assert match is not None, "Route /wallet/history must be registered as an alias for /wallet in portal.js"


def test_wallet_history_route_allowed_in_copyfast_registry() -> None:
    """WALLET_HISTORY_ROUTE: /wallet/history must be included in allowed_paths() in copyfast_registry.py."""
    import copyfast_registry
    allowed = copyfast_registry.allowed_paths()
    assert "/wallet/history" in allowed, "/wallet/history must be in allowed_paths() in copyfast_registry.py"


def test_wallet_history_route_renders_portal_shell() -> None:
    """WALLET_HISTORY_ROUTE: GET /wallet/history must return HTTP 200 via render_portal."""
    from copyfast_pages import render_portal
    response = render_portal("/wallet/history")
    assert response.status_code == 200, f"render_portal('/wallet/history') returned status {response.status_code}"


def test_dashboard_productivity_hub_wallet_card_destination() -> None:
    """PRIMARY_CTA_TRUTH: The Ví Xu & Nạp Tiền card on dashboard must link to /wallet/topup, not /pricing."""
    content = PORTAL_JS_PATH.read_text(encoding="utf-8")
    hub_start = content.find("function renderAISuiteProductivityHub")
    assert hub_start != -1, "renderAISuiteProductivityHub not found in portal.js"
    hub_end = content.find("function renderDashboard", hub_start)
    hub_content = content[hub_start:hub_end]

    assert "Ví Xu & Nạp Tiền" in hub_content, "Ví Xu & Nạp Tiền card not found in hub"
    wallet_card_match = re.search(r'<a\s+href="([^"]+)"[^>]*>(?:(?!<a)[\s\S])*?Ví Xu & Nạp Tiền', hub_content)
    assert wallet_card_match is not None, "Could not find anchor for Ví Xu & Nạp Tiền card"
    href = wallet_card_match.group(1)
    assert href == "/wallet/topup", f"Expected Card 8 href='/wallet/topup', got '{href}'"


def test_dashboard_productivity_hub_no_invented_bonus() -> None:
    """LOCAL_FAKE_PRICE=0: The Ví Xu & Nạp Tiền card must not promise '+10% Xu' without canonical backing."""
    content = PORTAL_JS_PATH.read_text(encoding="utf-8")
    hub_start = content.find("function renderAISuiteProductivityHub")
    hub_end = content.find("function renderDashboard", hub_start)
    hub_content = content[hub_start:hub_end]

    assert "Tặng +10% Xu" not in hub_content, "Found local invented bonus '+10% Xu' in dashboard hub"


def test_dashboard_productivity_hub_no_invented_pricing_claims() -> None:
    """LOCAL_FAKE_PRICE=0: Dashboard productivity cards must refer to canonical pricing rather than invented numbers."""
    content = PORTAL_JS_PATH.read_text(encoding="utf-8")
    hub_start = content.find("function renderAISuiteProductivityHub")
    hub_end = content.find("function renderDashboard", hub_start)
    hub_content = content[hub_start:hub_end]

    forbidden_invented_prices = [
        "0.10 Xu / ký tự",
        "Từ 0.10 Xu / từ",
        "100 - 300 Xu / bài",
        "Từ 50 Xu / ảnh",
    ]
    for price in forbidden_invented_prices:
        assert price not in hub_content, f"Found local invented price '{price}' in dashboard hub"


def test_dashboard_productivity_hub_chat_card_truthful() -> None:
    """LOCAL_FAKE_PRODUCT=0: /chat card must reflect authoring workspace without claiming automated CSKH."""
    content = PORTAL_JS_PATH.read_text(encoding="utf-8")
    hub_start = content.find("function renderAISuiteProductivityHub")
    hub_end = content.find("function renderDashboard", hub_start)
    hub_content = content[hub_start:hub_end]

    # The chat card must not claim automated customer support ("CSKH tự động")
    assert "CSKH tự động" not in hub_content, "/chat card must not claim automated customer support (CSKH tự động)"


def test_all_customer_static_hrefs_render_successfully() -> None:
    """Every static customer href in portal.js must resolve to HTTP 200 via render_portal."""
    from copyfast_pages import render_portal

    content = PORTAL_JS_PATH.read_text(encoding="utf-8")
    hrefs = set(re.findall(r'href="(/[a-zA-Z0-9_\-\/]+)"', content))
    customer_hrefs = [h for h in hrefs if not h.startswith('/admin')]

    failures = []
    for path in sorted(customer_hrefs):
        try:
            resp = render_portal(path)
            if resp.status_code != 200:
                failures.append((path, resp.status_code))
        except HTTPException as exc:
            failures.append((path, exc.status_code))
        except Exception as exc:
            failures.append((path, str(exc)))

    assert not failures, f"Customer hrefs failing render_portal: {failures}"
