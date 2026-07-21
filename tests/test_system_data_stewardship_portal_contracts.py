"""Focused static contracts for the Web-native System & Data Stewardship hubs."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _function_source(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    next_start = source.find("\n  function ", start + len(marker))
    return source[start:] if next_start < 0 else source[start:next_start]


def test_stewardship_routes_are_explicitly_server_guarded_and_not_public_catalog_actions() -> None:
    app = _read("app.py")
    registry = _read("copyfast_registry.py")
    navigation = _read("copyfast_admin_erp_navigation.py")

    assert 'elif normalized == "/admin/system-stewardship":\n        copyfast_auth.require_admin(request)' in app
    assert 'WebFeature("workspace_care", "Chăm sóc dữ liệu Web", "account", "/account/workspace-care"' in registry
    assert 'WebFeature("admin_system_stewardship", "System & Data Stewardship", "admin", "/admin/system-stewardship", "admin"' in registry
    assert '"web_system_stewardship"' in navigation
    assert '"/admin/system-stewardship"' in navigation
    assert 'authority="web_local_admin"' in navigation
    assert "local_admin_navigation_to_separately_guarded_read_surfaces" in navigation


def test_portal_hubs_are_navigation_only_and_preserve_authority_boundaries() -> None:
    portal = _read("static/portal/portal.js")
    integration = _read("static/portal/integration.js")
    css = _read("static/portal/portal.css")

    for declaration in (
        'customerPage("/account/workspace-care", "Chăm sóc dữ liệu Web"',
        'layout: "workspace-care", fields: [], action: "none", status: "read_only"',
        'adminPage("/admin/system-stewardship", "System & Data Stewardship"',
        'layout: "admin-system-stewardship", action: "none", status: "read_only"',
        'case "workspace-care": return renderWorkspaceCare(page, context);',
        'case "admin-system-stewardship": return renderAdminSystemStewardship(page, context);',
        'function serverAuthorizesAdminRoute(context, route)',
    ):
        assert declaration in portal

    workspace = _function_source(portal, "renderWorkspaceCare")
    stewardship = _function_source(portal, "renderAdminSystemStewardship")
    for route in ("/notes", "/reminders", "/account/data-controls"):
        assert route in workspace
    for route in (
        "/admin/automation",
        "/admin/security",
        "/admin/access",
        "/admin/governance",
        "/admin/internal-documents",
        "/admin/system",
        "/admin/runtime",
        "/admin/backups",
    ):
        assert route in stewardship
    for renderer in (workspace, stewardship):
        assert "data-portal-action" not in renderer
        assert "fetch(" not in renderer
        assert "api(" not in renderer
        assert "readAdminPath(" not in renderer
        assert "menu|" not in renderer
    assert "serverAuthorizesAdminRoute(context, card.route)" in stewardship
    assert "hasLiveCanonicalAdmin(context)" in stewardship
    assert "portal-workspace-care-card" in css
    assert "portal-stewardship-card" in css
    assert "@media (prefers-reduced-motion: reduce)" in css

    for declaration in (
        "function isNativeWorkspaceCarePath(path)",
        "function isNativeAdminSystemStewardshipPath(path)",
        '"/account/workspace-care": account ? "read_only" : "guarded"',
        '"/admin/system-stewardship": account ? "read_only" : "guarded"',
        "!isNativeWorkspaceCarePath(currentPath)",
        "!isNativeAdminSystemStewardshipPath(currentPath)",
        "!isNativeAdminSystemStewardshipPath(expectedPath)",
    ):
        assert declaration in integration


def test_audit_contract_is_finite_and_keeps_payment_video_and_bot_state_out_of_browser() -> None:
    audit = _read("scripts/migration/audit_bot_to_web.py")

    assert "SYSTEM_DATA_STEWARDSHIP_FRESH_WEB_NAVIGATION_ACTIONS" in audit
    assert '"menu|system": {' in audit
    assert '"menu|system_backup_help": {' in audit
    assert '"menu|internal_archive": {' in audit
    assert '"menu|memory_storage_cleanup": {' in audit
    assert '"SYSTEM_DATA_STEWARDSHIP_CALLBACK_CONTRACT.md"' in audit
    assert "reviewed_system_data_stewardship_fresh_web_navigation" in audit
    assert "NO_BACKUP_OR_RESTORE_ACTION" in audit
    assert "NO_STORAGE_DELETE_OR_QUOTA_CLAIM" in audit
    registry_slice = audit[audit.index("SYSTEM_DATA_STEWARDSHIP_FRESH_WEB_NAVIGATION_ACTIONS"):audit.index("GUIDED_VIDEO_MENU_DEFERRED_ACTIONS")]
    assert "menu|billing" not in registry_slice
    assert "menu|tax_" not in registry_slice
    assert "menu|video_" not in registry_slice
