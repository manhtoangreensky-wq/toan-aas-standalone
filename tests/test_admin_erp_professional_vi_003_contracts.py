"""Focused contracts for ADMIN-ERP-PROFESSIONAL-VI-003."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static/portal/portal.js"
I18N_PATH = ROOT / "static/portal/portal-i18n.js"
PORTAL = PORTAL_PATH.read_text(encoding="utf-8")
I18N = I18N_PATH.read_text(encoding="utf-8")
THEME = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")
CSS_MARKER = "/* Admin ERP Professional VI 003"
ADMIN_ROOT = '.portal-shell[data-portal-app-kind="admin"]'


def _between(source: str, start: str, end: str) -> str:
    start_index = source.index(start)
    return source[start_index : source.index(end, start_index + len(start))]


def _contains(source: str, *values: str) -> None:
    for value in values:
        assert value in source, value


def _excludes(source: str, *values: str) -> None:
    for value in values:
        assert value not in source, value


def _admin_catalogue() -> dict[str, dict[str, str]]:
    node = shutil.which("node")
    assert node, "Node is required to inspect the real Portal i18n catalogue"
    script = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");
const documentElement = { lang: "vi", dir: "ltr", setAttribute() {} };
const document = { documentElement, title: "", getElementById() { return null; } };
const context = {
  document, console, JSON, URL, URLSearchParams,
  CustomEvent: function CustomEvent(type, init) { this.type = type; this.detail = init && init.detail; },
  dispatchEvent() { return true; }
};
context.globalThis = context;
vm.createContext(context);
vm.runInContext(source, context, { filename: process.argv[1] });
const api = context.TOANAASI18n;
const output = {};
for (const locale of ["vi", "en", "zh"]) {
  output[locale] = Object.fromEntries(Object.entries(api.messages[locale]).filter(([key]) =>
    key.startsWith("adminHome.") || key.startsWith("adminErpNavigation.") || key.startsWith("summary.")
  ));
}
process.stdout.write(JSON.stringify(output));
'''
    result = subprocess.run([node, "-e", script, str(I18N_PATH)], check=False, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def _fixed_fallbacks(function_body: str) -> list[str]:
    values = re.findall(r'(?:adminText|uiText)\(\s*"[^"]+"\s*,\s*"((?:\\.|[^"\\])*)"', function_body)
    values.extend(re.findall(r">\s*([^<>{}\n]*[A-Za-zÀ-ỹ][^<>{}\n]*)\s*<", function_body))
    return values


def _admin_fallback_entries() -> dict[str, str]:
    functions = {
        "renderAdminDirectory": _between(PORTAL, "function renderAdminDirectory(context)", "function renderAdminWorkQueues(context)"),
        "renderAdminWorkQueues": _between(PORTAL, "function renderAdminWorkQueues(context)", "function renderAdminOverview(page, context)"),
        "renderAdminOverview": _between(PORTAL, "function renderAdminOverview(page, context)", "function renderAdminSystemStewardship(page, context)"),
    }
    return {f"fallback.{name}.{index}": value for name, body in functions.items() for index, value in enumerate(_fixed_fallbacks(body))}


def _without_placeholders(value: str) -> str:
    return re.sub(r"\{[^{}]+\}", "", value)


def _has_token(value: str, token: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(token)}(?!\w)", value, flags=re.IGNORECASE) is not None


def _css_rule(css: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{([^{}]*)\}", css)
    assert match, selector
    return match.group(1)


def test_admin_overview_accepts_all_three_server_authorized_modes_without_widening_routes() -> None:
    overview = _between(PORTAL, "function renderAdminOverview(page, context)", "function renderAdminSystemStewardship(page, context)")
    stewardship = _between(PORTAL, "function renderAdminSystemStewardship(page, context)", "function renderAdminDomain(page, context)")
    assert overview.count("adminErpNavigation(context)") == 1
    _contains(overview, "const navigation = adminErpNavigation(context);", "navigation.canonicalAdmin", "navigation.webLocalAdmin", 'navigation.supportRole !== "none"', "const serverAuthorized =", "const statusTitle = serverAuthorized")
    _contains(stewardship, "serverAuthorizesAdminRoute(context, card.route)", 'authority !== "canonical" || canonicalAdmin')


def test_admin_vietnamese_fixed_copy_is_scoped_and_free_of_forbidden_jargon() -> None:
    forbidden = ("Web", "CRM", "canonical", "Core Bridge", "FastAPI", "signed", "authority", "readiness", "provider", "engine", "worker", "queue", "job", "module", "adapter", "Admin ERP", "ERP ·", "CSRF")
    entries = {**_admin_catalogue()["vi"], **_admin_fallback_entries()}
    violations = [f"{key}={raw!r} [token={token}]" for key, raw in entries.items() for token in forbidden if _has_token(_without_placeholders(raw), token)]
    assert violations == [], "Vietnamese Admin copy contains fixed jargon:\n" + "\n".join(violations)
    assert "Phân hệ được máy chủ cấp cho phiên này" in entries.values()
    assert "Nhóm phân hệ được máy chủ cấp cho phiên này" in entries.values()


def test_admin_chinese_fixed_copy_has_no_unreviewed_latin_tokens() -> None:
    names = re.compile(r"TOAN AAS|PayOS|Telegram|Google|Apple|Xu", flags=re.IGNORECASE)
    violations = []
    for key, raw in _admin_catalogue()["zh"].items():
        latin = sorted(set(re.findall(r"[A-Za-z]+(?:[-_][A-Za-z]+)*", names.sub("", _without_placeholders(raw)))))
        if latin:
            violations.append(f"{key}={raw!r} [latin={','.join(latin)}]")
    assert violations == [], "Chinese Admin copy contains unreviewed Latin tokens:\n" + "\n".join(violations)


def test_admin_english_fixed_copy_is_english_and_free_of_internal_jargon() -> None:
    vietnamese = re.compile(r"[ăâđêôơưàáạảãầấậẩẫằắặẳẵèéẹẻẽềếệểễìíịỉĩòóọỏõồốộổỗờớợởỡùúụủũừứựửữỳýỵỷỹ]", flags=re.IGNORECASE)
    han = re.compile(r"[\u3400-\u9fff]")
    jargon = ("canonical", "Core Bridge", "FastAPI", "signed session", "read_only", "Web-native", "authority")
    violations = []
    for key, raw in _admin_catalogue()["en"].items():
        value = _without_placeholders(raw)
        reasons = (["Vietnamese"] if vietnamese.search(value) else []) + (["Han"] if han.search(value) else []) + [token for token in jargon if _has_token(value, token)]
        if reasons:
            violations.append(f"{key}={raw!r} [reason={','.join(reasons)}]")
    assert violations == [], "English Admin copy is mixed or exposes internal jargon:\n" + "\n".join(violations)


def test_render_summary_uses_reviewed_locale_keys_for_every_fixed_label_and_state() -> None:
    summary = _between(PORTAL, "function renderSummary(page, context)", "function renderNotes(page, labels)")
    keys = ("summary.title", "summary.subtitle", "summary.workspace", "summary.workspace.ready", "summary.workspace.login", "summary.companion", "summary.companion.connected", "summary.companion.optional", "summary.session", "summary.session.verified", "summary.session.pending", "summary.requestProtection", "summary.requestProtection.ready", "summary.requestProtection.pending", "summary.serverConnection", "summary.serverConnection.configured", "summary.serverConnection.pending")
    catalogue = _admin_catalogue()
    _contains(summary, 'const summaryText = (key, fallback) => uiText(key, fallback);')
    for key in keys:
        assert f'summaryText("{key}"' in summary
        for locale in ("vi", "en", "zh"):
            assert catalogue[locale].get(key, "").strip(), f"{locale}:{key}"
    _excludes(summary, "Bảo đảm luồng", "Trạng thái không được suy đoán ở client.", "Web Workspace", "Bot companion", "Signed session", "API base")


def test_admin_header_reuses_signed_locale_action_and_excludes_customer_chrome() -> None:
    header = _between(PORTAL, "function renderHeader(page, context)", "function renderFields(fields, enabled, context, fieldValues, idNamespace)")
    _contains(header, "const canOfferPwaInstall = Boolean(!adminSurface &&", "const currentLocale = interfaceLocaleFor(context);", "const adminHeaderLocaleForm = adminSurface", 'data-portal-action="update-interface-locale"', 'data-portal-route="/admin"', 'name="locale"', 'value="${value}"', "const customerUserDropdown =", "const adminUserDropdown =", "adminSurface ? adminUserDropdown : customerUserDropdown")
    for locale in ("vi", "en"):
        assert f'localeOption("{locale}",' in header
    locale_form = _between(header, "const adminHeaderLocaleForm =", "const customerUserDropdown =")
    header_actions = _between(header, '<div class="portal-header-actions">', "</div>`;")
    customer = _between(header, "const customerUserDropdown =", "const adminUserDropdown =")
    admin = _between(header, "const adminUserDropdown =", "const userDropdown =")
    _contains(header_actions, "${adminHeaderLocaleForm}")
    _excludes(locale_form, 'localeOption("zh",')
    _contains(customer, '<span style="font-size:11px; font-weight:700; background:rgba(255,255,255,0.1); color:${headerTierInfo.currentTier.color}; padding:1px 6px; border-radius:4px; border:1px solid ${headerTierInfo.currentTier.color}44;">${safeText(headerTierInfo.currentTier.badge)}</span>', '<a class="portal-user-dropdown-item" href="/admin" style="background: rgba(0, 242, 254, 0.08); border-left: 3px solid #00f2fe;">', '<div><strong style="color:#00f2fe;">⚙️ Trang Quản Trị Admin ERP</strong><small>Quản lý người dùng, duyệt Xu, tài chính & hệ thống</small></div>')
    _contains(admin, 'href="/account"', 'href="/account/security"', 'data-portal-action="auth-logout"')
    _excludes(admin, "${adminHeaderLocaleForm}", 'data-portal-action="update-interface-locale"')
    for key in ("account.profile", "account.profile_description", "account.security", "account.security_description", "accountCenter.profile.logoutConfirm", "accountCenter.profile.logout"):
        assert f'uiText("{key}"' in admin
    _excludes(admin, 'href="/membership"', 'href="/wallet"', 'href="/wallet/topup"', 'href="/admin"')


def test_admin_sidebar_has_no_primary_action_and_keeps_customer_create_markup() -> None:
    sidebar = _between(PORTAL, "function renderSidebar(page, context)", "function renderHeader(page, context)")
    _contains(sidebar, 'const sidebarActionRow = adminSurface ? "" :', "${sidebarActionRow}", 'href="/features"><span class="portal-sidebar-create-icon"', 'uiText("chrome.newWorkflow", "Tạo workflow mới")')
    _excludes(sidebar, "adminOverview", "adminRoutes")


def test_admin_removes_smart_install_and_copilot_before_they_render() -> None:
    smart = _between(PORTAL, "function syncSmartInstallBanner()", "function dismissSmartInstallBanner()")
    copilot = _between(PORTAL, "function mountPortalAiCopilot(context)", "window.TOANAASPortal")
    _contains(smart, "const isAdminSurface =", "isStandaloneApp() || isAuthPage || isAdminSurface", 'document.querySelector("[data-portal-smart-install-banner]")', 'document.querySelector("[data-portal-pwa-fab]")', "return;")
    _contains(copilot, "const isAdminPath =", "isAuthPage || !isAuthenticated || isAdminPath", 'container.innerHTML = "";', "container.remove();", "return;")


def test_admin_home_and_directory_are_compact_data_first_surfaces() -> None:
    overview = _between(PORTAL, "function renderAdminOverview(page, context)", "function renderAdminSystemStewardship(page, context)")
    directory = _between(PORTAL, "function renderAdminDirectory(context)", "function renderAdminWorkQueues(context)")
    navigation = _between(PORTAL, "function adminErpNavigation(context)", "function adminRouteIcon(route)")
    _excludes(overview, "renderHero(", "portal-admin-guard", 'String(counts.users || "—")')
    _contains(overview, "portal-admin-titlebar", "const metricValue =")
    assert overview.count("<h1") == 1
    _contains(directory, "portal-admin-directory-list", "portal-admin-directory-row", "moduleCard(entry, context")
    _excludes(directory, "portal-module-grid")
    _contains(navigation, 'const localizedModuleDescription = adminDeliveryRuntimeNavigationText(route, "description", moduleDescription);', 'const localizedGroupDescription = adminDeliveryRuntimeGroupText(id, "description", description);')
    _excludes(navigation, "useVietnameseMetadataFallback")
    _contains(I18N, '"adminErpNavigation.route.providers.description"', '"adminErpNavigation.group.supportOperations.description"')


def test_admin_i18n_catalogue_has_direct_reviewed_nonempty_copy_for_all_locales() -> None:
    _excludes(I18N, "Protected legacy source comparator only", '["adminHome.directory." + "title"]', "ADMIN_ERP_DESCRIPTION_FALLBACK_MESSAGES")
    assert I18N.count('"adminHome.directory.title":') == 3
    for translation in ("Danh mục phân hệ", "Module directory", "模块目录"):
        assert f'"adminHome.directory.title": "{translation}"' in I18N
    for copy in ('"adminErpNavigation.group.supportOperations": "Customer Care & Operations"', '"adminErpNavigation.group.supportOperations.description": "Customer support requests and operational work."', '"adminErpNavigation.route.providers": "Providers & costs"', '"adminErpNavigation.route.providers.description": "Review provider connections and summarized costs."', '"adminErpNavigation.group.supportOperations": "客户服务与运营"', '"adminErpNavigation.group.supportOperations.description": "客户支持请求与运营工作。"', '"adminErpNavigation.route.providers": "服务商与成本"', '"adminErpNavigation.route.providers.description": "查看服务商连接与汇总成本。"'):
        assert copy in I18N
    assert '"adminErpNavigation.route.overview": "Tổng quan"' in I18N
    for translation in ("Tìm trong quản trị", "Search administration", "搜索管理功能"):
        assert f'"chrome.searchAdmin": "{translation}"' in I18N
    for translation in ("{count} mục quản trị có thể mở trong phiên này.", "{count} administration destinations are available in this session.", "此会话可打开 {count} 个管理入口。"):
        assert f'"chrome.adminCommandCount": "{translation}"' in I18N
    palette = _between(PORTAL, "function renderCommandPalette(page, context)", "function renderSidebar(page, context)")
    command_filter = _between(PORTAL, "function filterCommandPalette(value)", "function closeCommandPalette(options)")
    navigation = _between(PORTAL, "function adminErpNavigation(context)", "function adminRouteIcon(route)")
    for body in (palette, command_filter):
        _excludes(body, "Tìm điều hướng ERP", "mục ERP")
    _contains(palette, "Tìm trong quản trị")
    _contains(palette + command_filter, "mục quản trị")
    _excludes(navigation, 'candidate.title || "Admin ERP"')
    _excludes(palette, 'module.title || "Admin ERP"')


def test_admin_css_override_is_scoped_dense_visible_and_responsive() -> None:
    assert CSS_MARKER in THEME
    css = THEME[THEME.index(CSS_MARKER):]
    selectors = re.findall(r"(?:^|\})\s*([^@{}][^{}]*)\{", re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL))
    for group in selectors:
        for selector in group.split(","):
            if not selector.strip().startswith("@"):
                assert selector.strip().startswith(ADMIN_ROOT), selector
    for contract in ("grid-template-columns: minmax(0, 1fr);", "padding: var(--portal-space-3);", "display: none;", "font-size: 16px;", "opacity: 1;", "transform: none;", "animation: none;", "@media (max-width: 700px)", "@media (prefers-reduced-motion: reduce)"):
        assert contract in css
    assert re.search(r"#[0-9a-fA-F]{3,8}\b", css) is None
    _excludes(css, "rgba(", "linear-gradient", "glow", "page-enter", "opacity: 0", "translate", "scale(", "@keyframes", "!important")
    mobile_index = css.index("@media (max-width: 700px)")
    desktop_css, mobile_css = css[:mobile_index], css[mobile_index:]
    broad_touch = re.compile(re.escape(ADMIN_ROOT) + r" button,\s*" + re.escape(ADMIN_ROOT) + r" a,\s*" + re.escape(ADMIN_ROOT) + r" select,\s*" + re.escape(ADMIN_ROOT) + r" summary\s*\{\s*min-height: 44px;")
    assert broad_touch.search(desktop_css) is None
    assert broad_touch.search(mobile_css) is not None
    for selector in (".portal-admin-work-queue", ".portal-admin-directory-group > summary", ".portal-admin-directory-row .portal-module-card", ".portal-admin-locale-form select"):
        assert re.search(re.escape(ADMIN_ROOT) + r"[^{}]*" + re.escape(selector) + r"[^{}]*\{[^{}]*min-height: 44px;", desktop_css)


def test_admin_r5_cascade_contract_wins_geometry_density_contrast_and_clipping() -> None:
    css = THEME[THEME.index(CSS_MARKER):]
    shell = ADMIN_ROOT + ":not(.portal-shell--auth):not(.portal-shell--landing)"
    row = ADMIN_ROOT + " .portal-page.portal-admin-home .portal-admin-directory-group .portal-admin-directory-row .portal-module-card"
    _contains(_css_rule(css, shell), "grid-template-columns: 240px minmax(0, 1fr);")
    _contains(_css_rule(css, shell + " .portal-header"), "box-sizing: border-box;", "height: 56px;", "min-height: 56px;")
    _contains(_css_rule(css, row), "height: 40px;", "min-height: 40px;", "overflow: hidden;")
    _contains(css, row + " h3", row + " p", "color: var(--portal-muted-strong);", "color: var(--portal-ink);", "overflow: visible;", "line-height: 1.2;")
    mobile = css[css.index("@media (max-width: 700px)"):]
    assert re.search(re.escape(row) + r"\s*\{[^{}]*height: auto;[^{}]*min-height: 44px;", mobile)


def test_admin_r6_cascade_contract_prevents_clipping_and_low_contrast() -> None:
    css = THEME[THEME.index(CSS_MARKER):]
    metric = ADMIN_ROOT + " .portal-page.portal-admin-home > .portal-admin-grid > .portal-metric strong"
    count = ADMIN_ROOT + " .portal-feature-count"
    arrow = ADMIN_ROOT + " .portal-module-arrow"
    hint = ADMIN_ROOT + " .portal-data-table-scroll-hint"
    row = ADMIN_ROOT + " .portal-page.portal-admin-home .portal-admin-directory-group .portal-admin-directory-row .portal-module-card"

    _contains(_css_rule(css, metric), "display: block;", "padding-block: var(--portal-space-1);", "overflow: visible;", "line-height: 1.1;")
    _contains(_css_rule(css, count), "color: var(--portal-ink);")
    _contains(_css_rule(css, arrow), "color: var(--portal-action);")
    _contains(_css_rule(css, hint), "color: var(--portal-muted-strong);", "border-color: var(--portal-border);", "background: var(--portal-surface-soft);")

    mobile = css[css.index("@media (max-width: 700px)"):]
    _contains(_css_rule(mobile, row), "height: auto;", "min-height: 44px;")
    _contains(
        _css_rule(mobile, row + " h3"),
        "white-space: normal;",
        "overflow: visible;",
        "text-overflow: clip;",
        "overflow-wrap: anywhere;",
    )


def test_contract_module_stays_within_owner_file_limit() -> None:
    assert len(Path(__file__).read_text(encoding="utf-8").splitlines()) <= 300
