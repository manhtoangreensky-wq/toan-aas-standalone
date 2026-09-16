"""Contract tests for Admin UI Visual Reset to Light Modern Teal/Emerald ERP.

TASK: P0.WEB.ADMIN.UI.PR454.VISUAL.EVIDENCE.CORRECTION.GATE
PROGRAM: P0.WEB.ERP.PRODUCTION_COMPLETION
"""

import json
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]
PORTAL_THEME_JS = (ROOT / "static" / "portal" / "portal-theme.js").read_text(encoding="utf-8")
PORTAL_THEME_CSS = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
PORTAL_JS = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
SERVICE_WORKER_JS = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")
AFTER_MANIFEST_PATH = ROOT / "reports" / "visual_reset" / "after" / "capture_manifest.json"
COMPUTED_COLORS_PATH = ROOT / "reports" / "visual_reset" / "after" / "computed_colors.json"


def test_admin_ui_theme_storage_key_isolation() -> None:
    """Admin theme preference must be stored in a dedicated key isolated from customer."""
    assert 'const ADMIN_THEME_STORAGE_KEY = "toan-aas-admin-theme-v2";' in PORTAL_THEME_JS
    assert 'const STORAGE_KEY = "toan-aas-portal-theme";' in PORTAL_THEME_JS
    assert "function isAdminRoute()" in PORTAL_THEME_JS
    assert 'pathname === "/admin" || pathname.startsWith("/admin/")' in PORTAL_THEME_JS
    assert "function currentStorageKey()" in PORTAL_THEME_JS
    assert "isAdminRoute() ? ADMIN_THEME_STORAGE_KEY : STORAGE_KEY" in PORTAL_THEME_JS


def test_admin_ui_default_appearance_is_light() -> None:
    """Admin default appearance must resolve strictly to light without user action."""
    assert 'if (isAdminRoute()) return "light";' in PORTAL_THEME_JS
    assert "adminStorageKey: ADMIN_THEME_STORAGE_KEY" in PORTAL_THEME_JS
    assert "isAdminRoute," in PORTAL_THEME_JS


def test_customer_theme_behavior_preserved() -> None:
    """Customer routes must preserve their default 'system' and shared storage key."""
    assert 'const STORAGE_KEY = "toan-aas-portal-theme";' in PORTAL_THEME_JS
    assert 'const THEMES = Object.freeze(["system", "light", "dark"]);' in PORTAL_THEME_JS
    assert ': "system";' in PORTAL_THEME_JS


def test_admin_ui_canvas_and_surfaces_forbid_obsidian() -> None:
    """Admin default appearance must be light teal/emerald; obsidian black is forbidden."""
    assert '.portal-shell[data-portal-app-kind="admin"]:not([data-portal-theme="dark"])' in PORTAL_THEME_CSS
    assert '--portal-app-canvas: #f3fbfc;' in PORTAL_THEME_CSS
    assert 'background: var(--portal-app-canvas) !important;' in PORTAL_THEME_CSS

    admin_auth_block = re.search(
        r'\.portal-body--auth\[data-portal-app-kind="admin"\]\s*\{(?P<rules>[^}]+)\}',
        PORTAL_CSS
    )
    if admin_auth_block:
        assert "#08111a" not in admin_auth_block.group("rules")
        assert "#09090b" not in admin_auth_block.group("rules")


def test_admin_ui_sidebar_is_crisp_light_with_teal_accent() -> None:
    """Admin sidebar must be crisp white with light border and teal indicators."""
    assert '.portal-shell[data-portal-app-kind="admin"]:not([data-portal-theme="dark"]) .portal-sidebar' in PORTAL_THEME_CSS
    assert 'background: var(--portal-surface-light) !important;' in PORTAL_THEME_CSS
    assert 'border-right: 1px solid var(--portal-admin-light-rail-border) !important;' in PORTAL_THEME_CSS


def test_admin_ui_data_tables_and_filters_are_light_surfaces() -> None:
    """Data table wrappers and filter boxes must render clean white surfaces in admin."""
    assert '.portal-shell[data-portal-app-kind="admin"]:not([data-portal-theme="dark"]) .portal-data-table-wrap' in PORTAL_THEME_CSS
    assert '.portal-shell[data-portal-app-kind="admin"]:not([data-portal-theme="dark"]) .portal-project-filter' in PORTAL_THEME_CSS
    assert '.portal-shell[data-portal-app-kind="admin"]:not([data-portal-theme="dark"]) .portal-empty-cell' in PORTAL_THEME_CSS


def test_admin_ui_diagnostics_disclosure_declutters_technical_readiness() -> None:
    """Secondary readiness/authority tables must be tucked into a disclosure widget."""
    assert 'portal-admin-diagnostics-disclosure' in PORTAL_JS
    assert 'portal-admin-topup-hero' in PORTAL_JS
    assert 'HÀNG ĐỢI DUYỆT TIỀN' in PORTAL_JS
    assert 'Mở hàng đợi nạp tiền →' in PORTAL_JS


def test_admin_login_light_teal_surface() -> None:
    """Admin login screen must render with light teal gradient canvas and white card."""
    assert '.portal-shell--auth[data-portal-app-kind="admin"]:not([data-portal-theme="dark"])' in PORTAL_THEME_CSS
    assert '.portal-shell--auth[data-portal-app-kind="admin"]:not([data-portal-theme="dark"]) .portal-auth-card' in PORTAL_THEME_CSS
    assert '.portal-shell--auth[data-portal-app-kind="admin"]:not([data-portal-theme="dark"]) .portal-button--primary' in PORTAL_THEME_CSS


def test_service_worker_skip_waiting_and_clients_claim() -> None:
    """Service worker must skip waiting and claim clients to avoid stale caches."""
    assert "self.skipWaiting()" in SERVICE_WORKER_JS
    assert "self.clients.claim()" in SERVICE_WORKER_JS
    assert 'const CACHE_PREFIX = "toan-aas-portal-shell-";' in SERVICE_WORKER_JS
    assert "const PRIVATE_PATH_PREFIXES" in SERVICE_WORKER_JS


def test_admin_ui_mobile_drawer_off_canvas_rules() -> None:
    """Admin mobile sidebar must be fixed off-canvas (-105%) and only slide in when open."""
    assert "@media (max-width: 980px)" in PORTAL_THEME_CSS
    assert '.portal-shell[data-portal-app-kind="admin"] .portal-sidebar' in PORTAL_THEME_CSS
    assert "transform: translateX(-105%) !important;" in PORTAL_THEME_CSS
    assert '.portal-shell[data-portal-app-kind="admin"] .portal-sidebar.is-open' in PORTAL_THEME_CSS
    assert "transform: translateX(0) !important;" in PORTAL_THEME_CSS


def test_admin_ui_mobile_screenshots_have_zero_cross_route_duplicates() -> None:
    """All 5 mobile screenshots must have unique SHA256 hashes proving distinct route identity."""
    if not AFTER_MANIFEST_PATH.exists():
        pytest.skip("Manifest not generated yet")
    manifest = json.loads(AFTER_MANIFEST_PATH.read_text(encoding="utf-8"))
    mobile_items = [item for item in manifest if "390" in item["viewport"]]
    assert len(mobile_items) == 5
    hashes = [item["screenshotSha256"] for item in mobile_items]
    assert len(set(hashes)) == 5, f"Cross-route duplicate detected in mobile screenshots: {hashes}"


def test_admin_ui_desktop_screenshots_have_zero_cross_route_duplicates() -> None:
    """All 5 desktop screenshots must have unique SHA256 hashes proving distinct route identity."""
    if not AFTER_MANIFEST_PATH.exists():
        pytest.skip("Manifest not generated yet")
    manifest = json.loads(AFTER_MANIFEST_PATH.read_text(encoding="utf-8"))
    desktop_items = [item for item in manifest if "1440" in item["viewport"]]
    assert len(desktop_items) == 5
    hashes = [item["screenshotSha256"] for item in desktop_items]
    assert len(set(hashes)) == 5, f"Cross-route duplicate detected in desktop screenshots: {hashes}"


def test_admin_ui_computed_colors_measured_values() -> None:
    """Computed colors must show light teal canvas and not-applicable for routes without CTA."""
    if not COMPUTED_COLORS_PATH.exists():
        pytest.skip("Computed colors not generated yet")
    colors = json.loads(COMPUTED_COLORS_PATH.read_text(encoding="utf-8"))
    for route in ("admin_home", "admin_customers", "admin_finance", "admin_jobs"):
        assert colors[route]["themeAttr"] == "light"
        assert colors[route]["bodyBg"] == "rgb(243, 251, 252)"
        assert colors[route]["sidebarBg"] == "rgb(255, 255, 255)"
    # Finance and Jobs have no primary CTA
    assert colors["admin_finance"]["primaryActionBg"] == "NOT_APPLICABLE"
    assert colors["admin_jobs"]["primaryActionBg"] == "NOT_APPLICABLE"
    # Admin login has emerald-teal primary CTA
    assert colors["admin_login"]["primaryActionBg"] in ("rgb(13, 148, 136)", "rgb(15, 118, 110)")


def test_admin_ui_semantic_tokens_have_no_self_referential_cycles() -> None:
    """Admin light semantic alias block must not contain self-referential cycles like --X: var(--X)."""
    match = re.search(
        r'\.portal-shell\[data-portal-app-kind=["\']admin["\']\]:not\(\[data-portal-theme=["\']dark["\']\]\)[^{]*\{(?P<rules>[^}]+)\}',
        PORTAL_THEME_CSS,
    )
    assert match is not None, "Admin light theme selector block not found in portal-theme.css"
    rules = match.group("rules")
    cycles = [
        prop
        for prop, val in re.findall(r"(--[a-zA-Z0-9_-]+)\s*:\s*var\(\s*(--[a-zA-Z0-9_-]+)\s*\)", rules)
        if prop == val
    ]
    assert not cycles, f"Self-referential custom property cycles detected in Admin light theme: {cycles}"
