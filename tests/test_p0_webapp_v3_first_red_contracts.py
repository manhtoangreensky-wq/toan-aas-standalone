"""First-Red Contract Tests for P0.WEBAPP.V3.UI.UX.THEME.NAV.RUNTIME.ERROR.FULL.REMEDIATION.

Master Program: P0.WEBAPP.FULL.PRODUCT.TRUTH.REMEDIATION.V1
Task: P0.WEBAPP.V3.UI.UX.THEME.NAV.RUNTIME.ERROR.FULL.REMEDIATION
Mode: OWNER-GOVERNED, WEBAPP_ONLY, TEST_FIRST_RED
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import pytest

from copyfast_registry import allowed_paths

ROOT = Path(__file__).resolve().parent.parent
PORTAL_THEME_CSS_PATH = ROOT / "static" / "portal" / "portal-theme.css"
PORTAL_FIRST_PAINT_CSS_PATH = ROOT / "static" / "portal" / "portal-first-paint.css"
PORTAL_THEME_JS_PATH = ROOT / "static" / "portal" / "portal-theme.js"
PORTAL_SHELL_HTML_PATH = ROOT / "templates" / "portal_shell.html"
PORTAL_JS_PATH = ROOT / "static" / "portal" / "portal.js"
INTEGRATION_JS_PATH = ROOT / "static" / "portal" / "integration.js"
CUSTOMER_APP_HTML_PATH = ROOT / "customer_app.html"

PORTAL_THEME_CSS = PORTAL_THEME_CSS_PATH.read_text(encoding="utf-8")
PORTAL_FIRST_PAINT_CSS = PORTAL_FIRST_PAINT_CSS_PATH.read_text(encoding="utf-8")
PORTAL_THEME_JS = PORTAL_THEME_JS_PATH.read_text(encoding="utf-8")
PORTAL_SHELL_HTML = PORTAL_SHELL_HTML_PATH.read_text(encoding="utf-8")
PORTAL_JS = PORTAL_JS_PATH.read_text(encoding="utf-8")
CUSTOMER_APP_HTML = CUSTOMER_APP_HTML_PATH.read_text(encoding="utf-8")


def _extract_customer_nav_groups() -> list[tuple[str, list[list[str]]]]:
    """Extract customer navigation groups and links from portal.js navGroups."""
    start = PORTAL_JS.index("function navGroups(context, currentPage)")
    end = PORTAL_JS.index("const currentGroup = currentCustomerWorkflowGroup")
    nav_block = PORTAL_JS[start:end]

    group_matches = re.findall(
        r'label:\s*"([^"]+)"[^[]*links:\s*\[(.*?)\]\s*\}', nav_block, re.DOTALL
    )
    groups = []
    for label, links_str in group_matches:
        links = re.findall(r'\["(/[^"]+)",\s*"([^"]+)"', links_str)
        groups.append((label, links))
    return groups


def _extract_customer_mobile_dock_links() -> list[tuple[str, str, str]]:
    """Extract customer mobile bottom dock links from portal.js renderMobileNav."""
    start = PORTAL_JS.index("function renderMobileNav(page)")
    end = PORTAL_JS.index("function isAdminMobileSurface(page)")
    block = PORTAL_JS[start:end]
    return re.findall(r'\["([^"]+)",\s*"(/[^"]+)",\s*uiText\("[^"]+",\s*"([^"]+)"\)', block)


def _node_classify_error(status: int, payload: dict | None) -> str:
    """Execute classifyError from integration.js directly via Node."""
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for classifyError contract")
    integration_js = INTEGRATION_JS_PATH.read_text(encoding="utf-8")
    start = integration_js.index("const MUTATION_HTTP_RETRY_POLICY =")
    end = integration_js.index("async function api(path, options)")
    fn_code = integration_js[start:end]
    payload_json = json.dumps(payload) if payload is not None else "undefined"
    node_script = f"""
    {fn_code}
    const status = {status};
    const payload = {payload_json};
    const result = classifyError(status, payload);
    process.stdout.write(result);
    """
    res = subprocess.run([node, "-e", node_script], capture_output=True, text=True, check=True)
    return res.stdout.strip()


class TestP0WebappV3FirstRedContracts:
    """Rigorous First-Red validation confirming all 7 gaps before implementation."""

    def test_red_01_blue_tokens_purged_from_theme_and_first_paint(self) -> None:
        """Gap 1: Blue tokens must be fully purged from portal-theme.css, first-paint, and shell."""
        assert "--portal-customer-blue-rail: #075985" not in PORTAL_THEME_CSS, (
            "Legacy --portal-customer-blue-rail: #075985 still present in portal-theme.css"
        )
        assert "--portal-admin-blue-rail: #075985" not in PORTAL_THEME_CSS, (
            "Legacy --portal-admin-blue-rail: #075985 still present in portal-theme.css"
        )
        assert "--portal-blue-action: #0284c7" not in PORTAL_THEME_CSS, (
            "Legacy --portal-blue-action: #0284c7 still present in portal-theme.css"
        )
        assert "#f0f9ff" not in PORTAL_FIRST_PAINT_CSS, (
            "Legacy blue tint #f0f9ff still present in portal-first-paint.css"
        )
        assert "#f0f9ff" not in PORTAL_SHELL_HTML, (
            "Legacy blue tint #f0f9ff still present in portal_shell.html"
        )
        assert "#0b2545" not in PORTAL_SHELL_HTML, (
            "Legacy dark navy #0b2545 still present in portal_shell.html"
        )

    def test_red_02_customer_primary_navigation_exact_13_links_and_4_tiers(self) -> None:
        """Gap 2: Customer navigation must have exactly 13 canonical links across 4 Tiers."""
        groups = _extract_customer_nav_groups()
        assert len(groups) == 4, f"Expected 4 tiers, got {len(groups)}"

        all_links = []
        for _, links in groups:
            all_links.extend(links)
        assert len(all_links) == 13, f"Expected exactly 13 links, got {len(all_links)}"

        expected_routes_by_tier = [
            ["/studio", "/voice", "/music", "/subdub", "/tools/video", "/tools/image"],
            ["/publishing"],
            ["/projects", "/tools/free"],
            ["/pricing", "/wallet", "/account", "/support"],
        ]
        for i, expected_routes in enumerate(expected_routes_by_tier):
            tier_label, tier_links = groups[i]
            tier_routes = [link[0] for link in tier_links]
            assert tier_routes == expected_routes, (
                f"Tier {i+1} ({tier_label}) mismatch: expected {expected_routes}, got {tier_routes}"
            )

    def test_red_03_video_studio_subroutes_not_spliced_into_primary_sidebar(self) -> None:
        """Gap 3: Video Studio subroutes must NOT be spliced into primary sidebar rail."""
        start = PORTAL_JS.index("function navGroups(context, currentPage)")
        end = PORTAL_JS.index("function matchesRouteFamily(path, root)", start)
        nav_block = PORTAL_JS[start:end]
        assert "videoStudioNavGroups" not in nav_block, (
            "videoStudioNavGroups is still spliced into customer primary navigation rail"
        )
        assert "matchesRouteFamily(currentRoute, \"/video-studio\")" not in nav_block, (
            "video-studio route splicing is still active in navGroups"
        )

    def test_red_04_canonical_routes_in_allowed_paths(self) -> None:
        """Gap 4: Canonical routes (/studio, /publishing, etc.) must be in allowed_paths."""
        paths = allowed_paths()
        for route in ("/studio", "/publishing", "/voice", "/music", "/subdub", "/tools/video", "/tools/image", "/tools/free"):
            assert route in paths, f"Canonical route {route} missing from allowed_paths()"

    def test_red_05_telegram_409_unlinked_card_contract_present(self) -> None:
        """Gap 5: Telegram 409 unlinked card contract must be present in portal.js."""
        assert "portal-telegram-unlinked-card" in PORTAL_JS, (
            "portal-telegram-unlinked-card component missing from portal.js"
        )
        assert "ACCOUNT_TELEGRAM_UNLINKED" in PORTAL_JS, (
            "ACCOUNT_TELEGRAM_UNLINKED handling missing from portal.js"
        )

    def test_red_06_customer_mobile_dock_5_canonical_tabs(self) -> None:
        """Gap 6: Customer mobile bottom dock must have the 5 canonical tabs."""
        dock_links = _extract_customer_mobile_dock_links()
        assert len(dock_links) == 5, f"Expected 5 mobile dock links, got {len(dock_links)}"
        dock_routes = [d[1] for d in dock_links]
        expected = ["/studio", "/publishing", "/projects", "/wallet", "/account"]
        assert dock_routes == expected, f"Mobile dock routes mismatch: expected {expected}, got {dock_routes}"

    def test_red_07_customer_app_html_inline_blue_purged(self) -> None:
        """Gap 7: Inline blue CSS in customer_app.html must be purged."""
        assert "#eff6ff" not in CUSTOMER_APP_HTML, (
            "Inline blue #eff6ff still present in customer_app.html"
        )
        assert "#2563eb" not in CUSTOMER_APP_HTML, (
            "Inline blue #2563eb still present in customer_app.html"
        )

    def test_red_08_classify_error_409_requires_authoritative_telegram_unlinked_signal(self) -> None:
        """Gap 8: HTTP 409 without authoritative Telegram-unlinked signal must classify as VALIDATION_4XX."""
        # 1. Unrelated 409 payloads MUST NOT return ACCOUNT_TELEGRAM_UNLINKED_409
        unrelated_payloads = [
            {"code": "REVISION_CONFLICT"},
            {"error": "conflict"},
            {"message": "resource state conflict"},
            {},
            None,
        ]
        for payload in unrelated_payloads:
            result = _node_classify_error(409, payload)
            assert result != "ACCOUNT_TELEGRAM_UNLINKED_409", (
                f"Generic 409 with payload {payload} misclassified as ACCOUNT_TELEGRAM_UNLINKED_409"
            )
            assert result == "VALIDATION_4XX", (
                f"Generic 409 with payload {payload} expected VALIDATION_4XX, got {result}"
            )

        # 2. Telegram-unlinked evidence MUST still classify correctly when payload has canonical signals
        canonical_signals = [
            {"code": "ACCOUNT_TELEGRAM_UNLINKED"},
            {"error": "telegram_unlinked"},
            {"error_code": "ACCOUNT_TELEGRAM_UNLINKED_409"},
        ]
        for payload in canonical_signals:
            result = _node_classify_error(409, payload)
            assert result == "ACCOUNT_TELEGRAM_UNLINKED_409", (
                f"Canonical signal {payload} must classify as ACCOUNT_TELEGRAM_UNLINKED_409, got {result}"
            )

        # 3. Preserved regression classifications
        assert _node_classify_error(502, {}) == "TRANSPORT_502"
        assert _node_classify_error(503, {}) == "TRANSPORT_502"
        assert _node_classify_error(504, {}) == "TRANSPORT_502"
        assert _node_classify_error(404, {}) == "UPSTREAM_NOT_FOUND_404"
        assert _node_classify_error(401, {}) == "AUTH_401_403"
        assert _node_classify_error(403, {}) == "AUTH_401_403"
        assert _node_classify_error(422, {}) == "VALIDATION_4XX"
