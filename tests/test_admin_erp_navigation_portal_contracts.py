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
    palette = portal[
        portal.index("function commandPaletteItems(context, page)"):
        portal.index("function renderCommandPalette(page, context)")
    ]

    assert "function adminErpNavigation(context)" in portal
    assert "webLocalAdmin" in portal
    assert "The ERP navigation directory is a small server-authorized projection" in portal
    assert "adminErpNavigation: source.adminErpNavigation" in portal
    assert "function serverAuthorizesAdminRoute(context, route)" in portal
    assert "const authorizedAdminRoutes = adminErpNavigation(context).routes;" in portal
    assert "if (candidate.access === \"admin\" && !authorizedAdminRoutes.has(path)) return;" in portal
    assert "function adminNavigationModules(context)" in portal
    assert "function adminDesktopNavGroups(context, currentPage)" in portal
    assert "if (adminSurface)" in palette
    assert "adminErpNavigation(context).groups.forEach" in palette
    assert "authorizedAdminRoutes.has(path)" in palette
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


def test_admin_mobile_dock_is_server_granted_compact_and_never_reuses_customer_routes() -> None:
    portal = _read("static/portal/portal.js")
    shared = portal[
        portal.index("function adminNavigationModules(context)"):
        portal.index("function navGroups(context, currentPage)")
    ]
    helpers = portal[
        portal.index("function isAdminMobileSurface(page)"):
        portal.index("function normalizeCommandSearch(value)")
    ]

    # The compact ERP dock is a presentation of the signed server manifest,
    # never a browser-owned role map or a customer-nav fallback.
    assert "const navigation = adminErpNavigation(context);" in shared
    assert "if (!navigation.groups.length) return [];" in shared
    assert "const MAX_ADMIN_MOBILE_NAV_ITEMS = 5;" in helpers
    assert "navigation.routes.has(module.route)" in shared
    assert "serverAuthorizesAdminRoute(context, path)" in helpers
    assert "group.modules.forEach" in shared
    assert "const modules = adminNavigationModules(context);" in helpers
    assert "renderAdminMobileNav(page, context)" in helpers
    assert 'href="${safeText(item.route)}"' in helpers
    assert "safeText(item.title)" in helpers
    assert "portalIcon(item.icon)" in helpers
    assert "if (!items.length) return \"\";" in helpers
    assert "fetch(" not in helpers
    assert "dispatchAction(" not in helpers
    assert "context.isAdmin" not in helpers
    assert "context.role" not in helpers
    assert "renderMobileNav(" not in helpers
    assert '"/dashboard"' not in helpers
    assert '"/features"' not in helpers

    current = helpers[
        helpers.index("function isAdminMobileNavCurrent(module, path, context)"):
        helpers.index("const MAX_ADMIN_MOBILE_NAV_ITEMS = 5;")
    ]
    # A detail route can only inherit the two server-defined staff roots;
    # there is deliberately no general `/admin/*` current-state shortcut.
    assert 'module.route === "/admin/jobs"' in current
    assert 'module.route === "/admin/support"' in current
    assert 'path.startsWith("/admin/jobs/")' in current
    assert 'path.startsWith("/admin/support/")' in current
    assert 'module.route === "/admin" && path.startsWith("/admin/")' not in current


def test_admin_desktop_sidebar_uses_only_server_authorized_groups() -> None:
    portal = _read("static/portal/portal.js")

    assert "function isAdminPortalSurface(page)" in portal
    assert "function adminNavigationModules(context)" in portal
    assert "function currentAdminNavigationModule(page, context, modules)" in portal
    assert "function adminDesktopNavGroups(context, currentPage)" in portal

    helpers = portal[
        portal.index("function adminNavigationModules(context)"):
        portal.index("function navGroups(context, currentPage)")
    ]
    navigation = portal[
        portal.index("function navGroups(context, currentPage)"):
        portal.index("function matchesRouteFamily(path, root)")
    ]

    assert "const navigation = adminErpNavigation(context);" in helpers
    assert "navigation.routes.has(module.route)" in helpers
    assert "const issuedRoutes = new Set(issued.map((module) => module.route));" in helpers
    assert "context.isAdmin" not in helpers
    assert '"/dashboard"' not in helpers
    assert '"/features"' not in helpers
    assert "if (isAdminPortalSurface(currentPage)) return adminDesktopNavGroups(context, currentPage);" in navigation


def test_full_admin_manifest_uses_a_shared_bounded_group_limit_not_a_ten_group_truncation() -> None:
    integration = _read("static/portal/integration.js")
    portal = _read("static/portal/portal.js")

    assert "const MAX_ADMIN_ERP_NAVIGATION_GROUPS = 16;" in integration
    assert "rawGroups.slice(0, MAX_ADMIN_ERP_NAVIGATION_GROUPS)" in integration
    assert "rawGroups.slice(0, 10)" not in integration

    assert "const MAX_ADMIN_ERP_NAVIGATION_GROUPS = 16;" in portal
    assert "source.adminErpNavigation.groups.slice(0, MAX_ADMIN_ERP_NAVIGATION_GROUPS)" in portal
    assert "source.groups.slice(0, MAX_ADMIN_ERP_NAVIGATION_GROUPS)" in portal
    assert "source.adminErpNavigation.groups.slice(0, 10)" not in portal
    assert "source.groups.slice(0, 10)" not in portal
    # The mobile dock deliberately stays compact even when desktop/sidebar and
    # command palette retain every group that the signed server manifest grants.
    assert "const MAX_ADMIN_MOBILE_NAV_ITEMS = 5;" in portal
