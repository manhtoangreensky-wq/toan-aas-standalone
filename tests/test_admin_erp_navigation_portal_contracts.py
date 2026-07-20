"""Static contracts for the server-authorized Admin ERP Portal navigation."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_portal_hydrates_a_server_authorized_admin_manifest_and_fails_closed() -> None:
    integration = _read("static/portal/integration.js")
    app = _read("app.py")

    assert "import copyfast_admin_erp_navigation" in app
    assert "app.include_router(copyfast_admin_erp_navigation.router)" in app
    assert 'api("/admin/navigation")' in integration
    assert "adminErpNavigationEpoch" in integration
    assert "normalizeAdminErpNavigation" in integration
    assert "web_local_admin" in integration
    assert "Fail closed: an unavailable manifest hides all ERP shortcuts" in integration
    assert "WEBAPP_ADMIN_ERP_ENABLED" not in integration
    assert '"/admin/providers": "/admin/providers"' in integration
    assert '"packages"' in integration
    assert "isNativeAdminSecurityAccessPosturePath" in integration
    assert '"/admin/security"' in integration
    assert '"/admin/access"' in integration
    assert '"audit", "security", "access", "reports"' not in integration


def test_portal_sidebar_directory_and_palette_use_the_server_manifest_not_browser_role() -> None:
    portal = _read("static/portal/portal.js")

    assert "function adminErpNavigation(context)" in portal
    assert "webLocalAdmin" in portal
    assert "The ERP navigation directory is a small server-authorized projection" in portal
    assert "adminErpNavigation: source.adminErpNavigation" in portal
    assert "function serverAuthorizesAdminRoute(context, route)" in portal
    assert "const authorizedAdminRoutes = adminErpNavigation(context).routes;" in portal
    assert "if (candidate.access === \"admin\" && !authorizedAdminRoutes.has(path)) return;" in portal
    assert "const erp = adminErpNavigation(context);" in portal
    assert "erp.groups.forEach" in portal
    assert "context.isAdmin) {\n      groups.push({\n        label: \"Admin ERP\"" not in portal


def test_admin_navigation_does_not_create_direct_provider_or_payment_authority() -> None:
    backend = _read("copyfast_admin_erp_navigation.py")
    worker = _read("static/portal/service-worker.js")

    assert "metadata contains no records, counts, secrets" in backend
    assert "Every write remains behind its own server-side permission, CSRF, confirmation, idempotency and audit contract." in backend
    assert "Web CRM Governance is a local, redacted read-only directory" in backend
    assert "internal_handoff_review_with_server_role_check" in backend
    assert "redacted_cross_account_pipeline_read_only" in backend
    assert "request.json" not in backend
    assert "Body(" not in backend
    assert "@router.get(\"/navigation\")" in backend
    assert "@router.post" not in backend
    assert '"/" + "api/v1/admin"' in worker
    assert '"/admin"' in worker
