"""Executable contracts for A09 Admin Locale Gap 24 completion.

Ensures that all 50 canonical Admin routes have complete, verified,
bilingual/trilingual Title and Description metadata across VI, EN, and ZH.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTAL_JS = ROOT / "static" / "portal" / "portal.js"
PORTAL_I18N_JS = ROOT / "static" / "portal" / "portal-i18n.js"
REPORT_JSON = ROOT / "reports" / "audit" / "A09-ADMIN-EXHAUSTIVE-LOCALE-AUDIT-001.json"


def _between(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def _get_all_50_routes() -> list[str]:
    audit = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    return sorted([r["route"] for r in audit["routes"]])


def test_admin_export_included_in_admin_erp_route_i18n() -> None:
    portal_text = PORTAL_JS.read_text(encoding="utf-8")
    reg_src = _between(portal_text, "const ADMIN_ERP_ROUTE_I18N", "function adminErpGroupText")
    
    assert '"/admin/export": "adminErpNavigation.route.export"' in reg_src, (
        "/admin/export must be registered in ADMIN_ERP_ROUTE_I18N"
    )
    
    routes_in_registry = set(re.findall(r'"(/admin[^"]*)":', reg_src))
    all_routes = set(_get_all_50_routes())
    assert all_routes.issubset(routes_in_registry), (
        f"Missing routes in ADMIN_ERP_ROUTE_I18N: {all_routes - routes_in_registry}"
    )


def test_localized_page_title_and_description_cover_all_50_routes() -> None:
    portal_text = PORTAL_JS.read_text(encoding="utf-8")
    
    # localizedPageTitle must fall back to ADMIN_ERP_ROUTE_I18N[path]
    title_fn = _between(portal_text, "function localizedPageTitle(page, context)", "function documentTitle")
    assert "ADMIN_ERP_ROUTE_I18N[path]" in title_fn, (
        "localizedPageTitle must consult ADMIN_ERP_ROUTE_I18N[path]"
    )
    
    # localizedPageDescription must fall back to ADMIN_ERP_ROUTE_I18N[path] and support /admin
    desc_fn = _between(portal_text, "function localizedPageDescription(page)", "function initials(name)")
    assert 'path === "/admin"' in desc_fn, (
        "localizedPageDescription must have a dedicated branch for /admin"
    )
    assert "ADMIN_ERP_ROUTE_I18N[path]" in desc_fn, (
        "localizedPageDescription must consult ADMIN_ERP_ROUTE_I18N[path]"
    )


def test_all_50_routes_resolve_distinct_locale_titles_and_descriptions_via_node() -> None:
    """Execute Node script to verify all 50 routes produce non-empty, localized text in VI, EN, ZH."""
    routes = _get_all_50_routes()
    assert len(routes) == 50

    gap_routes = [
        "/admin", "/admin/analytics", "/admin/approvals", "/admin/audit", "/admin/backups",
        "/admin/calendar", "/admin/campaigns", "/admin/customers", "/admin/export",
        "/admin/finance/planning", "/admin/governance", "/admin/growth",
        "/admin/internal-documents", "/admin/leads", "/admin/packages", "/admin/pricing",
        "/admin/promos", "/admin/publishing", "/admin/refunds", "/admin/reports",
        "/admin/revenue", "/admin/system", "/admin/trends", "/admin/wallet"
    ]

    node_script = """
    const fs = require('fs');
    global.window = global;
    global.window.location = { pathname: '/admin' };
    global.document = { querySelector: () => null, documentElement: { lang: 'vi', setAttribute: () => {} } };

    const i18nPath = process.argv[1];
    const portalPath = process.argv[2];
    const routes = JSON.parse(process.argv[3]);
    const gapRoutes = new Set(JSON.parse(process.argv[4]));

    eval(fs.readFileSync(i18nPath, 'utf-8'));
    const portalSource = fs.readFileSync(portalPath, 'utf-8');

    function extractBlock(source, startPattern, endPattern) {
        const start = source.indexOf(startPattern);
        if (start === -1) throw new Error("Start pattern not found: " + startPattern);
        const end = source.indexOf(endPattern, start);
        if (end === -1) throw new Error("End pattern not found: " + endPattern);
        return source.slice(start, end);
    }

    const normSrc = extractBlock(portalSource, "function normalizePath(path)", "const CAPABILITY_HUB_FAMILY_KEYS");
    eval("global.normalizePath = " + normSrc.replace("function normalizePath(path)", "function (path)"));

    const erpSrc = extractBlock(portalSource, "const ADMIN_ERP_ROUTE_I18N =", "function adminErpGroupText");
    eval("global.ADMIN_ERP_ROUTE_I18N = " + erpSrc.replace("const ADMIN_ERP_ROUTE_I18N =", ""));

    const uiText = (key, fallback, params) => {
        const translated = window.TOAN_AAS_I18N.t(key, params);
        return typeof translated === "string" && translated ? translated : fallback;
    };
    const displayPageTitle = (p) => p.title || "";
    const featureFamilyForPath = () => null;
    const adminDataViewRouteKey = (page) => {
        const p = normalizePath(page && (page.routePath || page.path));
        const map = {
            "/admin/users": "users",
            "/admin/jobs": "jobs",
            "/admin/payments": "payments",
            "/admin/providers": "providers",
            "/admin/tickets": "tickets"
        };
        return map[p] || null;
    };
    const ADMIN_DATA_VIEW_ROUTE_KEYS = {
        "/admin/users": "users",
        "/admin/jobs": "jobs",
        "/admin/payments": "payments",
        "/admin/providers": "providers",
        "/admin/tickets": "tickets"
    };
    const adminManualTopupText = (k, fb) => uiText("adminManualTopup." + k, fb);
    const adminFinanceText = (k, fb) => uiText("adminFinance." + k, fb);
    const adminGenericText = (k, fb) => uiText("adminGeneric." + k, fb);
    const adminSecurityAccessText = (k, fb) => adminGenericText("securityAccess." + k, fb);
    const adminAutomationMonitorText = (k, fb) => adminGenericText("automationMonitor." + k, fb);
    const adminSystemStewardshipText = (k, fb) => adminGenericText("systemStewardship." + k, fb);
    const adminPostbackReadinessText = (k, fb) => adminGenericText("postbackReadiness." + k, fb);
    const adminJobRecoveryGuideText = (k, fb) => adminGenericText("jobRecoveryGuide." + k, fb);
    const adminSupportText = (k, fb) => uiText("adminSupport." + k, fb);
    const adminOperationsText = (k, fb) => uiText("adminOperations." + k, fb);
    const adminContentHandoffText = (k, fb) => uiText("adminContentHandoff." + k, fb);
    const adminWorkQueueText = (k, fb) => uiText("adminWorkQueue." + k, fb);
    const adminCrmManagerText = (k, fb) => uiText("adminCrmManager." + k, fb);
    const adminDeliveryRuntimeNavigationText = (p, f, fb) => {
        const key = ADMIN_ERP_ROUTE_I18N[p];
        return key ? uiText(f === "title" ? key : key + ".description", fb) : fb;
    };
    const adminDataViewRouteText = (page, f, fb) => {
        const routeKey = adminDataViewRouteKey(page);
        return routeKey ? uiText(`adminDataView.route.${routeKey}.${f}`, fb) : fb;
    };
    const localizedNavigationLabel = (fb) => fb;

    const titleSrc = extractBlock(portalSource, "function localizedPageTitle(page, context)", "function documentTitle");
    eval("global.localizedPageTitle = " + titleSrc.replace("function localizedPageTitle(page, context)", "function (page, context)"));

    const descSrc = extractBlock(portalSource, "function localizedPageDescription(page)", "function initials(name)");
    eval("global.localizedPageDescription = " + descSrc.replace("function localizedPageDescription(page)", "function (page)"));

    const languages = ['vi', 'en', 'zh'];

    for (const r of routes) {
        const results = {};
        for (const lang of languages) {
            window.TOAN_AAS_I18N.setLocale(lang);
            const page = { routePath: r, path: r, title: "Fallback Title", description: "Fallback Description" };
            const title = localizedPageTitle(page, {});
            const desc = localizedPageDescription(page);

            if (!title || title === "Fallback Title") {
                console.error(`Route ${r} missing localized title for ${lang}: got "${title}"`);
                process.exit(1);
            }
            if (!desc || desc === "Fallback Description") {
                console.error(`Route ${r} missing localized description for ${lang}: got "${desc}"`);
                process.exit(2);
            }
            results[lang] = { title, desc };
        }
        // If this route is one of the 24 gap routes, verify full VI/EN/ZH distinction
        if (gapRoutes.has(r)) {
            if (results.vi.title === results.en.title) {
                console.error(`Gap Route ${r} VI and EN titles are identical: "${results.vi.title}"`);
                process.exit(3);
            }
            if (results.vi.title === results.zh.title) {
                console.error(`Gap Route ${r} VI and ZH titles are identical: "${results.vi.title}"`);
                process.exit(4);
            }
            if (results.vi.desc === results.en.desc) {
                console.error(`Gap Route ${r} VI and EN descriptions are identical: "${results.vi.desc}"`);
                process.exit(5);
            }
            if (results.vi.desc === results.zh.desc) {
                console.error(`Gap Route ${r} VI and ZH descriptions are identical: "${results.vi.desc}"`);
                process.exit(6);
            }
        }
    }
    console.log("ALL_50_ROUTES_VERIFIED_SUCCESS");
    """

    result = subprocess.run(
        ["node", "-e", node_script, str(PORTAL_I18N_JS), str(PORTAL_JS), json.dumps(routes), json.dumps(gap_routes)],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    assert result.returncode == 0, (
        f"Node execution failed: code {result.returncode}\n"
        f"Stdout: {result.stdout}\nStderr: {result.stderr}"
    )
    assert "ALL_50_ROUTES_VERIFIED_SUCCESS" in result.stdout
