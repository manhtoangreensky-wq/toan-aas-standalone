"""Contract tests for Admin UI Visual Reset to Light Modern Teal/Emerald ERP.

TASK: P0.WEB.ADMIN.UI.VISUAL.RESET.LIGHT.TEAL.LIVE.ACCEPTANCE
PROGRAM: P0.WEB.ERP.PRODUCTION_COMPLETION
"""

from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]
PORTAL_THEME_JS = (ROOT / "static" / "portal" / "portal-theme.js").read_text(encoding="utf-8")
PORTAL_THEME_CSS = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")
PORTAL_CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")
PORTAL_JS = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
SERVICE_WORKER_JS = (ROOT / "static" / "portal" / "service-worker.js").read_text(encoding="utf-8")


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
    assert 'background: #f3fbfc !important;' in PORTAL_THEME_CSS
    
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
    assert 'background: #ffffff !important;' in PORTAL_THEME_CSS
    assert 'border-right: 1px solid #e2edf0 !important;' in PORTAL_THEME_CSS


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
