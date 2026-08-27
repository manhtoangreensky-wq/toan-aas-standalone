"""Contracts for the Admin VI/EN Odoo-style shell."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static/portal/portal.js"
PORTAL = PORTAL_PATH.read_text(encoding="utf-8")
I18N = (ROOT / "static/portal/portal-i18n.js").read_text(encoding="utf-8")
THEME = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")
THEME_MARKER = "/* Admin VI/EN Shell 001 --------------------------------------------- */"


def _between(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def _run_node(body: str) -> dict[str, object]:
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
function extract(start, end) {
  const offset = source.indexOf(start);
  if (offset < 0) throw new Error(`missing ${start}`);
  const finish = source.indexOf(end, offset + start.length);
  if (finish < 0) throw new Error(`missing end ${end}`);
  return source.slice(offset, finish);
}
function adminErpNavigation(context) { return context.navigation; }
function normalizePath(value) { return value || "/"; }
function isAdminMobileNavCurrent(module, path) {
  return path === module.route
    || (module.route === "/admin/jobs" && path.startsWith("/admin/jobs/"))
    || (module.route === "/admin/support" && path.startsWith("/admin/support/"));
}
function safeText(value) { return String(value); }
function uiText(key, fallback, params) {
  return params && params.count ? fallback.replace("{count}", params.count) : fallback;
}
function portalIcon(icon) { return `<i>${icon}</i>`; }
eval(extract("function adminNavigationModules(context)", "function navGroups(context, currentPage)"));
const navigation = {
  routes: new Set(["/admin/payments", "/admin", "/admin/support"]),
  groups: [
    { id: "finance", title: "Tài chính", modules: [{ route: "/admin/payments", title: "Thanh toán", icon: "money" }] },
    { id: "core", title: "Hệ thống", modules: [{ route: "/admin", title: "Trung tâm điều hành", icon: "home" }] },
    { id: "support", title: "Hỗ trợ", modules: [{ route: "/admin/support", title: "Phiếu hỗ trợ", icon: "support" }] }
  ]
};
const context = { navigation };
''' + body
    result = subprocess.run(
        ["node", "-e", script, str(PORTAL_PATH)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_sidebar_renders_only_route_active_server_group_with_admin_fallback() -> None:
    result = _run_node(
        r'''
const support = adminDesktopNavGroups(context, { path: "/admin/support" });
const root = adminDesktopNavGroups(context, { path: "/admin" });
process.stdout.write(JSON.stringify({ support, root }));
'''
    )

    assert [group["label"] for group in result["support"]] == ["Hỗ trợ"]
    assert result["support"][0]["links"] == [["/admin/support", "Phiếu hỗ trợ", "support", True]]
    assert [group["label"] for group in result["root"]] == ["Hệ thống"]


def test_app_switcher_uses_every_server_group_and_first_module_route() -> None:
    result = _run_node(
        r'''
const html = renderAdminAppSwitcher({ path: "/admin/support" }, context);
process.stdout.write(JSON.stringify({
  appCount: (html.match(/class="portal-admin-app"/g) || []).length,
  routes: Array.from(html.matchAll(/href="([^"]+)"/g), (match) => match[1]),
  activeCount: (html.match(/aria-current="page"/g) || []).length,
  hasTitles: navigation.groups.every((group) => html.includes(group.title))
}));
'''
    )

    assert result == {
        "appCount": 3,
        "routes": ["/admin/payments", "/admin", "/admin/support"],
        "activeCount": 1,
        "hasTitles": True,
    }


def test_admin_locale_form_is_direct_header_action_and_only_offers_vi_en() -> None:
    header = _between(PORTAL, "function renderHeader(page, context)", "function renderFields(")
    actions = _between(header, '<div class="portal-header-actions">', "</div>`;")
    dropdown = _between(header, "const adminUserDropdown =", "const userDropdown =")
    form = _between(header, "const adminHeaderLocaleForm =", "const customerUserDropdown =")

    assert "${adminHeaderLocaleForm}" in actions
    assert "${adminHeaderLocaleForm}" not in dropdown
    assert 'data-portal-action="update-interface-locale"' in form
    assert 'data-portal-route="/admin"' in form
    assert 'name="locale"' in form
    assert 'localeOption("vi",' in form
    assert 'localeOption("en",' in form
    assert 'localeOption("zh",' not in form


def test_admin_shell_new_copy_has_exact_vi_en_keys() -> None:
    expected = {
        "vi": {
            "adminShell.apps": "Ứng dụng",
            "adminShell.modules": "phân hệ",
            "adminShell.currentApp": "Ứng dụng hiện tại",
            "adminShell.language": "Ngôn ngữ",
            "adminShell.applyLanguage": "Áp dụng",
        },
        "en": {
            "adminShell.apps": "Apps",
            "adminShell.modules": "modules",
            "adminShell.currentApp": "Current app",
            "adminShell.language": "Language",
            "adminShell.applyLanguage": "Apply",
        },
    }
    catalogue = _between(I18N, "const ADMIN_HOME_MESSAGES =", "const ADMIN_DATA_SURFACE_MESSAGES =")
    for messages in expected.values():
        for key, value in messages.items():
            assert f'"{key}": "{value}"' in catalogue


def test_admin_first_viewport_has_no_generic_enter_choreography() -> None:
    entrance = _between(
        THEME,
        "/* A regular tool/detail page gets one spatially continuous entrance.",
        "/* Only navigation-like cards respond to fine-pointer hover.",
    )

    assert 'data-portal-app-kind="admin"' not in entrance
    assert ".portal-admin-grid" not in entrance


def test_admin_takeover_css_locks_compact_header_locale_label_and_drawer() -> None:
    takeover = THEME[THEME.index("/* Admin VI/EN Shell 001") :]
    marker = "/* Admin VI/EN Shell Takeover 001 */"
    corrective = THEME[THEME.index(marker) :] if marker in THEME else ""

    assert "white-space: nowrap;" in corrective
    assert ".portal-admin-app-switcher-label" in corrective
    assert "flex: 0 0 72px;" in corrective
    assert "width: min(240px, calc(100vw - 42px));" in corrective
    assert "grid-template-columns: 44px minmax(0, 1fr) 44px 44px;" in corrective
    assert "grid-template-rows: 44px 44px;" in corrective
    assert "display: contents;" in corrective
    assert "flex-wrap: wrap;" in takeover


def test_admin_breadcrumb_inserts_active_app_between_brand_and_page() -> None:
    header = _between(PORTAL, "function renderHeader(page, context)", "function renderFields(")

    assert "const adminActiveGroup = adminSurface ? activeAdminNavigationGroup(page, context) : null;" in header
    assert "crumbItems.splice(1, 0, adminActiveGroup.title);" in header
    assert 'aria-current="page"' in header


def test_admin_shell_css_is_scoped_tokenized_and_mobile_safe() -> None:
    shell = THEME[THEME.index(THEME_MARKER) :]

    for contract in (
        'grid-template-columns: 240px minmax(0, 1fr);',
        "min-height: 64px;",
        "min-height: 56px;",
        "min-height: 44px;",
        "overflow-x: auto;",
        "overflow-x: hidden;",
        "border-bottom: 3px solid transparent;",
        "@media (max-width: 700px)",
    ):
        assert contract in shell
    assert "gradient" not in shell
    assert "glow" not in shell
    assert "!important" not in shell
    assert "rgba(" not in shell
    assert "#" not in shell
