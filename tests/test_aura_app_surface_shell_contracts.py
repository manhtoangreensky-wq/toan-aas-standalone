"""Red contracts for the distinct Customer App and Internal ERP shells.

This slice is intentionally presentation-only.  It may classify an already
resolved Portal page for styling, but it must never infer identity, discover
an Admin route, or create a new route/authority boundary in the browser.
"""

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL = (ROOT / "static" / "portal" / "portal.js").read_text(encoding="utf-8")
THEME = (ROOT / "static" / "portal" / "portal-theme.css").read_text(encoding="utf-8")


def _section(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset:source.index(end, offset + len(start))]


def test_surface_classifier_is_page_driven_and_preserves_existing_public_modes() -> None:
    classifier = _section(PORTAL, "function portalSurface(page)", "function mountPortal(override)")

    assert "page.layout === \"landing\"" in classifier
    assert "page.layout === \"auth\"" in classifier
    assert "isAdminPortalSurface(page)" in classifier
    assert 'return "customer";' in classifier
    assert "context.session" not in classifier
    assert "page.isAdmin" not in classifier
    assert "page.role" not in classifier
    assert "localStorage" not in classifier
    assert "sessionStorage" not in classifier


def test_surface_classifier_projects_each_resolved_page_kind_to_one_visual_shell() -> None:
    classifier = _section(PORTAL, "function portalSurface(page)", "function mountPortal(override)")

    runtime = "\n".join(
        (
            "function isAdminPortalSurface(page) {",
            "  const path = String(page && (page.routePath || page.path) || '');",
            "  return path === '/admin' || path.startsWith('/admin/');",
            "}",
            classifier,
            "const result = {",
            "  landing: portalSurface({ layout: 'landing', path: '/welcome' }),",
            "  auth: portalSurface({ layout: 'auth', path: '/login' }),",
            "  customer: portalSurface({ layout: 'customer', path: '/dashboard' }),",
            "  admin: portalSurface({ layout: 'customer', routePath: '/admin/jobs' })",
            "};",
            "process.stdout.write(JSON.stringify(result));",
        )
    )
    node = shutil.which("node")
    assert node is not None
    result = subprocess.run([node, "-e", runtime], check=False, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr or result.stdout
    assert json.loads(result.stdout) == {
        "landing": "landing",
        "auth": "auth",
        "customer": "customer",
        "admin": "admin",
    }


def test_mount_assigns_distinct_customer_and_admin_shell_classes_without_changing_nav_authority() -> None:
    mount = _section(PORTAL, "function mountPortal(override) {", "\n\n  window.TOANAASPortal")

    assert "const surface = portalSurface(page);" in mount
    assert 'shell.classList.toggle("portal-shell--customer", surface === "customer");' in mount
    assert 'shell.classList.toggle("portal-shell--admin", surface === "admin");' in mount
    assert 'document.body.classList.toggle("portal-body--customer", surface === "customer");' in mount
    assert 'document.body.classList.toggle("portal-body--admin", surface === "admin");' in mount
    assert "isAdminMobileSurface(page) ? renderAdminMobileNav(page, context) : renderMobileNav(page)" in mount
    assert "serverAuthorizesAdminRoute" not in _section(PORTAL, "function portalSurface(page)", "function mountPortal(override)")


def test_app_shell_theme_is_scoped_to_semantic_surface_tokens_and_keeps_dense_admin_reading_model() -> None:
    for selector in (
        '[data-portal-surface="customer"]',
        '[data-portal-surface="admin"]',
        '[data-portal-surface="customer"] .portal-header',
        '[data-portal-surface="admin"] .portal-header',
        '[data-portal-surface="customer"] .portal-mobile-nav',
        '[data-portal-surface="admin"] .portal-mobile-nav',
    ):
        assert selector in THEME

    assert "--portal-app-canvas" in THEME
    assert "--portal-surface-light" in THEME
    assert "--portal-border" in THEME
    assert "--portal-elevation-" in THEME
    assert '[data-portal-surface="admin"] .portal-data-table' in THEME
    assert '[data-portal-surface="admin"] .portal-admin-data-toolbar' in THEME


def test_app_shell_respects_existing_mobile_safety_and_reduced_motion_boundaries() -> None:
    assert "@media (max-width: 980px)" in THEME
    assert "var(--portal-safe-bottom)" in THEME
    assert "@media (prefers-reduced-motion: reduce)" in THEME
    assert '[data-portal-surface="customer"]' in THEME
    assert '[data-portal-surface="admin"]' in THEME
