"""RED contracts for A09 Admin Vertical Shell."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static/portal/portal.js"
PORTAL = PORTAL_PATH.read_text(encoding="utf-8")
I18N_PATH = ROOT / "static/portal/portal-i18n.js"
I18N = I18N_PATH.read_text(encoding="utf-8")
THEME_PATH = ROOT / "static/portal/portal-theme.css"
THEME = THEME_PATH.read_text(encoding="utf-8")
PORTAL_AUTH_PATH = ROOT / "static/portal/portal-auth.js"
PORTAL_AUTH = PORTAL_AUTH_PATH.read_text(encoding="utf-8")
THEME_JS_PATH = ROOT / "static/portal/portal-theme.js"
THEME_JS = THEME_JS_PATH.read_text(encoding="utf-8")
A09_CSS_MARKER = "/* A09 Admin Vertical Shell */"


def _between(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def _brace_body(source: str, token: str) -> str:
    match = re.search(re.escape(token) + r"\s*\{", source)
    assert match is not None, f"Missing exact CSS block: {token}"
    depth = 1
    for index in range(match.end(), len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[match.end() : index]
    raise AssertionError(f"Unclosed CSS block: {token}")


def _admin_home_locale_blocks() -> dict[str, str]:
    catalogue = _between(I18N, "const ADMIN_HOME_MESSAGES =", "const ADMIN_DATA_SURFACE_MESSAGES =")
    return {
        "vi": _between(catalogue, "vi: {", "en: {"),
        "en": _between(catalogue, "en: {", "zh: {"),
        "zh": catalogue[catalogue.index("zh: {") :],
    }


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
const window = { location: { pathname: "/admin" } };
const ICONS = Object.freeze({
  admin: "admin", support: "support", users: "users", payments: "payments",
  jobs: "jobs", providers: "providers", security: "security", reports: "reports",
  system: "system", default: "default", search: "search", download: "download",
  menu: "menu", close: "close", prompt: "prompt", dashboard: "dashboard", workboard: "workboard"
});
const ALLOWED_STATES = new Set(["ready", "guarded", "read_only"]);
const manifest = Object.freeze({});

function safeText(value, fallback) {
  if (typeof value !== "string") return fallback || "";
  return value.replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c]));
}

const MESSAGES = {
  "adminHome.title": "Trung tâm điều hành",
  "adminHome.description": "Theo dõi dữ liệu và công việc",
  "adminHome.guard.verifiedTitle": "Quyền quản trị đã được máy chủ xác nhận",
  "adminHome.guard.pendingTitle": "Đang chờ máy chủ xác minh",
  "adminHome.guard.verifiedBody": "Mọi thao tác đọc và ghi",
  "adminHome.guard.pendingBody": "Máy chủ phải xác minh",
  "adminHome.guard.kicker": "Trạng thái phiên",
  "adminHome.readiness.kicker": "Mức sẵn sàng",
  "adminHome.readiness.title": "Trạng thái hệ thống",
  "adminHome.readiness.body": "Chỉ xem trạng thái",
  "adminHome.readiness.refresh": "Làm mới",
  "adminHome.readiness.emptyTitle": "Chưa có trạng thái",
  "adminHome.readiness.emptyBody": "Máy chủ chỉ trả trạng thái",
  "adminHome.sourceEmpty.title": "Chưa có số liệu vận hành",
  "adminHome.sourceEmpty.body": "Dữ liệu sẽ xuất hiện khi máy chủ cung cấp nguồn đo hợp lệ.",
  "adminHome.sourceEmpty.action": "Làm mới dữ liệu",
  "adminHome.quickAccess.kicker": "Điều hướng theo quyền",
  "adminHome.quickAccess.title": "Truy cập nhanh",
  "adminHome.quickAccess.body": "Mở các phân hệ được máy chủ cấp cho phiên quản trị này.",
  "adminHome.authority.summary": "Quyền hạn và ranh giới quản trị",
  "chrome.openNavigation": "Mở điều hướng",
  "chrome.closeNavigation": "Đóng điều hướng"
};

function uiText(key, fallback, params) {
  let val = MESSAGES[key] || fallback || key || "";
  if (params && typeof params === "object") {
    Object.entries(params).forEach(([k, v]) => {
      val = val.replaceAll(`{${k}}`, String(v));
    });
  }
  return val;
}
function portalIcon(icon) { return `<svg data-icon="${icon}"></svg>`; }
function badge(state) { return `<span>${state}</span>`; }
function renderSummary() { return "<summary-stub></summary-stub>"; }
function moduleCard(module, context, label, options) { return `<div class="portal-module-card">${safeText(module && module.title || "")}</div>`; }
function renderRowsTable(headers, rows, rowRenderer, emptyTitle, emptyBody) {
  if (!rows || !rows.length) return `<div class="empty-table">${emptyTitle}</div>`;
  return `<table><tbody>${rows.map(rowRenderer).join("")}</tbody></table>`;
}

const runtime = [
  extract("const MAX_ADMIN_ERP_NAVIGATION_GROUPS = 16;", "function publicBuildId(value)"),
  extract("function normalizePath(path)", "const CAPABILITY_HUB_FAMILY_KEYS"),
  extract("function safeCatalogRoute(value)", "function catalogEntryRoute(entry)"),
  extract("function adminErpNavigation(context)", "function navGroups(context, currentPage)"),
  extract("function isAdminMobileNavCurrent(module, path, context)", "function renderAdminMobileNav("),
  extract("function renderAdminDirectory(context)", "function renderAdminSystemStewardship(page, context)"),
  extract("function setSidebarMenuState(button, opened)", "function mobileSidebarDialogSupported()")
].join("\n");
eval(runtime);
''' + body
    result = subprocess.run(
        ["node", "-e", script, str(PORTAL_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Node execution failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# 1A — Full Vertical Server Catalog
# ---------------------------------------------------------------------------


def test_admin_desktop_nav_groups_returns_all_thirteen_groups_in_server_order() -> None:
    result = _run_node(
        r'''
const groups = [
  { id: "command-center", title: "Trung tâm điều hành", modules: [
    { route: "/admin", title: "Tổng quan", state: "available" },
    { route: "/admin/tickets", title: "Phiếu yêu cầu", state: "available" }
  ]},
  { id: "support", title: "Hỗ trợ & Vận hành", modules: [
    { route: "/admin/support", title: "Phiếu hỗ trợ", state: "available" },
    { route: "/admin/users", title: "Người dùng", state: "available" }
  ]},
  { id: "crm", title: "Quan hệ khách hàng", modules: [
    { route: "/admin/crm/leads", title: "Khách hàng tiềm năng", state: "available" },
    { route: "/admin/crm/pipeline", title: "Quy trình bán hàng", state: "available" }
  ]},
  { id: "finance", title: "Tài chính", modules: [
    { route: "/admin/payments", title: "Thanh toán", state: "available" },
    { route: "/admin/finance/planning", title: "Kế hoạch tài chính", state: "available" }
  ]},
  { id: "delivery", title: "Xử lý & Phân phối", modules: [
    { route: "/admin/jobs", title: "Tác vụ", state: "available" },
    { route: "/admin/providers", title: "Nhà cung cấp", state: "available" }
  ]},
  { id: "content", title: "Nội dung & Tăng trưởng", modules: [
    { route: "/admin/campaigns", title: "Chiến dịch", state: "available" },
    { route: "/admin/publishing", title: "Xuất bản", state: "available" }
  ]},
  { id: "automation", title: "Tự động hóa", modules: [
    { route: "/admin/automation", title: "Lập lịch", state: "available" },
    { route: "/admin/automation/queues", title: "Hàng đợi tự động", state: "available" }
  ]},
  { id: "system", title: "Quản trị hệ thống", modules: [
    { route: "/admin/system-stewardship", title: "Giám sát hệ thống", state: "available" },
    { route: "/admin/runtime", title: "Thời gian chạy", state: "available" }
  ]},
  { id: "security", title: "Bảo mật", modules: [
    { route: "/admin/security", title: "An toàn hệ thống", state: "available" },
    { route: "/admin/access", title: "Quyền truy cập", state: "available" }
  ]},
  { id: "governance", title: "Quản trị & Hồ sơ", modules: [
    { route: "/admin/governance", title: "Văn bản quản trị", state: "available" },
    { route: "/admin/audit", title: "Nhật ký kiểm toán", state: "available" }
  ]},
  { id: "archive", title: "Kho lưu trữ", modules: [
    { route: "/admin/internal-documents", title: "Tài liệu nội bộ", state: "available" },
    { route: "/admin/archive/export", title: "Xuất lưu trữ", state: "available" }
  ]},
  { id: "growth", title: "Mở rộng & Tiếp thị", modules: [
    { route: "/admin/affiliates", title: "Tiếp thị liên kết", state: "available" },
    { route: "/admin/trends", title: "Xu hướng", state: "available" }
  ]},
  { id: "backups", title: "Sao lưu & Khôi phục", modules: [
    { route: "/admin/backups", title: "Bản sao lưu", state: "available" },
    { route: "/admin/recovery", title: "Khôi phục dữ liệu", state: "available" }
  ]}
];

const context = {
  adminErpNavigation: {
    read_state: "ready",
    groups
  }
};

const desktopGroups = adminDesktopNavGroups(context, { routePath: "/admin/jobs" });
const allLinks = desktopGroups.flatMap((g) => g.links);
const routes = allLinks.map((l) => l[0]);
const currentGroups = desktopGroups.filter((g) => g.current === true);
const openGroups = desktopGroups.filter((g) => g.defaultOpen === true);
const currentLinks = allLinks.filter((l) => l[3] === true);

process.stdout.write(JSON.stringify({
  groupCount: desktopGroups.length,
  groupLabels: desktopGroups.map((g) => g.label),
  currentGroupsCount: currentGroups.length,
  currentGroupLabel: currentGroups.length ? currentGroups[0].label : null,
  openGroupsCount: openGroups.length,
  routesCount: routes.length,
  routesUnique: new Set(routes).size === routes.length,
  currentLinkRoute: currentLinks.length === 1 ? currentLinks[0][0] : null,
  hasCustomerOrUnissued: routes.some((r) => r.startsWith("/dashboard") || r.startsWith("/features") || !r.startsWith("/admin"))
}));
'''
    )

    assert result["groupCount"] == 13, f"Expected 13 groups, got {result['groupCount']}"
    assert result["groupLabels"] == [
        "Trung tâm điều hành", "Hỗ trợ & Vận hành", "Quan hệ khách hàng", "Tài chính",
        "Xử lý & Phân phối", "Nội dung & Tăng trưởng", "Tự động hóa", "Quản trị hệ thống",
        "Bảo mật", "Quản trị & Hồ sơ", "Kho lưu trữ", "Mở rộng & Tiếp thị", "Sao lưu & Khôi phục",
    ]
    assert result["currentGroupsCount"] == 1
    assert result["openGroupsCount"] == 1
    assert result["currentGroupLabel"] == "Xử lý & Phân phối"
    assert result["currentLinkRoute"] == "/admin/jobs"
    assert result["routesCount"] == 26
    assert result["routesUnique"] is True
    assert result["hasCustomerOrUnissued"] is False


def test_admin_header_omits_horizontal_app_switcher_and_render_call() -> None:
    header_section = _between(PORTAL, "function renderHeader(page, context)", "function renderFields(")
    assert "renderAdminAppSwitcher" not in header_section
    assert "portal-admin-app-switcher" not in header_section
    assert "function renderAdminAppSwitcher" not in PORTAL


# ---------------------------------------------------------------------------
# 1C — Truthful Dashboard Hierarchy (Missing vs Real Data)
# ---------------------------------------------------------------------------


def test_dashboard_all_source_missing_renders_consolidated_empty_and_zero_metrics() -> None:
    result = _run_node(
        r'''
const context = {
  adminErpNavigation: {
    read_state: "ready",
    canonicalAdmin: true,
    groups: [{
      id: "command-center",
      title: "Trung tâm điều hành",
      modules: [{ route: "/admin", title: "Tổng quan", state: "available" }]
    }]
  },
  adminData: {
    counts: {},
    readiness: {}
  },
  capabilities: {
    "refresh-admin": true
  }
};

const html = renderAdminOverview({ routePath: "/admin" }, context);

const metricCount = (html.match(/class="portal-metric"/g) || []).length;
const panelCount = (html.match(/class="[^"]*portal-admin-dashboard-panel[^"]*"/g) || []).length;
const emptyCount = (html.match(/class="[^"]*portal-admin-dashboard-source-empty[^"]*"/g) || []).length;

process.stdout.write(JSON.stringify({
  metricCount,
  panelCount,
  emptyCount,
  hasSourceEmptyTitle: html.includes("Chưa có số liệu vận hành"),
  hasSourceEmptyBody: html.includes("Dữ liệu sẽ xuất hiện khi máy chủ cung cấp nguồn đo hợp lệ."),
  hasSourceEmptyAction: html.includes("Làm mới dữ liệu") || html.includes('data-portal-action="refresh-admin"')
}));
'''
    )

    assert result["metricCount"] == 0, f"Expected 0 metrics in missing-source state, got {result['metricCount']}"
    assert result["panelCount"] == 0, f"Expected 0 panels in missing-source state, got {result['panelCount']}"
    assert result["emptyCount"] == 1, f"Expected 1 source-empty container, got {result['emptyCount']}"
    assert result["hasSourceEmptyTitle"] is True
    assert result["hasSourceEmptyBody"] is True
    assert result["hasSourceEmptyAction"] is True


def test_dashboard_source_present_zero_renders_metrics() -> None:
    result = _run_node(
        r'''
const context = {
  adminErpNavigation: {
    read_state: "ready",
    canonicalAdmin: true,
    groups: [{
      id: "command-center",
      title: "Trung tâm điều hành",
      modules: [{ route: "/admin", title: "Tổng quan", state: "available" }]
    }]
  },
  adminData: {
    counts: { users: 0 },
    readiness: {}
  },
  capabilities: {
    "refresh-admin": true
  }
};

const html = renderAdminOverview({ routePath: "/admin" }, context);
const metricCount = (html.match(/class="portal-metric"/g) || []).length;
const emptyCount = (html.match(/class="[^"]*portal-admin-dashboard-source-empty[^"]*"/g) || []).length;

process.stdout.write(JSON.stringify({
  metricCount,
  emptyCount,
  hasZeroValue: html.includes("<strong>0</strong>")
}));
'''
    )

    assert result["metricCount"] == 1, f"Expected only the source-backed metric, got {result['metricCount']}"
    assert result["emptyCount"] == 0, f"Expected 0 source-empty container, got {result['emptyCount']}"
    assert result["hasZeroValue"] is True


def test_dashboard_real_data_preserves_workload_and_readiness() -> None:
    result = _run_node(
        r'''
const context = {
  adminErpNavigation: {
    read_state: "ready",
    canonicalAdmin: true,
    groups: [{
      id: "command-center",
      title: "Trung tâm điều hành",
      modules: [{ route: "/admin", title: "Tổng quan", state: "available" }]
    }]
  },
  adminData: {
    counts: { engine_jobs: 10, worker_jobs: 4, payments: 20 },
    readiness: {
      image: { public_ready: true, adapter: "image-local" },
      audio: { public_ready: false, adapter: "audio-local" }
    }
  }
};

const html = renderAdminOverview({ routePath: "/admin" }, context);
const panelCount = (html.match(/class="[^"]*portal-admin-dashboard-panel[^"]*"/g) || []).length;
const emptyCount = (html.match(/class="[^"]*portal-admin-dashboard-source-empty[^"]*"/g) || []).length;

process.stdout.write(JSON.stringify({
  panelCount,
  emptyCount,
  hasWorkloadBars: html.includes("portal-admin-workload-bar"),
  hasReadinessDonut: html.includes("portal-admin-readiness-donut")
}));
'''
    )

    assert result["panelCount"] == 2
    assert result["emptyCount"] == 0
    assert result["hasWorkloadBars"] is True
    assert result["hasReadinessDonut"] is True


def test_dashboard_partial_zero_unknown_and_readiness_only_are_source_truthful() -> None:
    result = _run_node(
        r'''
function receipt(counts, readiness) {
  const context = {
    adminErpNavigation: {
      read_state: "ready",
      canonicalAdmin: true,
      groups: [{ id: "command-center", title: "Trung tâm điều hành", modules: [{ route: "/admin", title: "Tổng quan", state: "available" }] }]
    },
    adminData: { counts, readiness },
    capabilities: { "refresh-admin": true }
  };
  const html = renderAdminOverview({ routePath: "/admin" }, context);
  const metrics = Array.from(
    html.matchAll(/class="portal-metric"[^>]*><span>([^<]*)<\/span><strong>([^<]*)<\/strong>/g),
    (match) => [match[1], match[2]]
  );
  const sourceEmpty = html.match(/<section[^>]*portal-admin-dashboard-source-empty[^>]*>[\s\S]*?<\/section>/)?.[0] || "";
  return {
    metrics,
    workloadPanels: (html.match(/portal-admin-workload-chart/g) || []).length,
    readinessPanels: (html.match(/portal-admin-readiness-chart/g) || []).length,
    sourceEmptyCount: (html.match(/portal-admin-dashboard-source-empty/g) || []).length,
    workloadEmpty: html.includes("Chưa có số liệu vận hành") && html.includes("portal-admin-workload-chart"),
    sourceEmptyHasOwnAction: sourceEmpty.includes('data-portal-action="refresh-admin"') && sourceEmpty.includes("Làm mới dữ liệu")
  };
}
process.stdout.write(JSON.stringify({
  missing: receipt({}, {}),
  usersZero: receipt({ users: 0 }, {}),
  workloadZero: receipt({ engine_jobs: 0, worker_jobs: 0, payments: 0 }, {}),
  unrelated: receipt({ unrelated_count: 9 }, {}),
  readinessOnly: receipt({}, {
    image: { public_ready: true, adapter: "image-local" },
    audio: { public_ready: false, adapter: "audio-local" }
  }),
  full: receipt({ users: 3, engine_jobs: 2, worker_jobs: 1, payments: 4 }, {
    image: { public_ready: true, adapter: "image-local" }
  })
}));
'''
    )

    assert result["missing"] == {
        "metrics": [],
        "workloadPanels": 0,
        "readinessPanels": 0,
        "sourceEmptyCount": 1,
        "workloadEmpty": False,
        "sourceEmptyHasOwnAction": True,
    }
    assert result["usersZero"]["metrics"] == [["Người dùng", "0"]]
    assert result["usersZero"]["workloadPanels"] == 0
    assert result["usersZero"]["readinessPanels"] == 0
    assert result["usersZero"]["sourceEmptyCount"] == 0
    assert result["workloadZero"]["metrics"] == [
        ["Tác vụ hệ thống", "0"],
        ["Tác vụ xử lý", "0"],
        ["Thanh toán", "0"],
    ]
    assert result["workloadZero"]["workloadPanels"] == 1
    assert result["workloadZero"]["readinessPanels"] == 0
    assert result["workloadZero"]["workloadEmpty"] is False
    assert result["unrelated"]["metrics"] == []
    assert result["unrelated"]["sourceEmptyCount"] == 1
    assert result["unrelated"]["workloadPanels"] == 0
    assert result["unrelated"]["readinessPanels"] == 0
    assert result["readinessOnly"]["metrics"] == [["Mức sẵn sàng", "1/2"]]
    assert result["readinessOnly"]["workloadPanels"] == 0
    assert result["readinessOnly"]["readinessPanels"] == 1
    assert result["full"]["metrics"] == [
        ["Người dùng", "3"],
        ["Tác vụ hệ thống", "2"],
        ["Tác vụ xử lý", "1"],
        ["Thanh toán", "4"],
        ["Mức sẵn sàng", "1/1"],
    ]
    assert result["full"]["workloadPanels"] == 1
    assert result["full"]["readinessPanels"] == 1


def test_render_admin_work_queues_uses_quick_access_locale_keys() -> None:
    result = _run_node(
        r'''
const context = {
  adminErpNavigation: {
    read_state: "ready",
    canonicalAdmin: true,
    routes: new Set(["/admin/support", "/admin/jobs", "/admin/payments", "/admin/users"]),
    groups: [{
      id: "support",
      title: "Hỗ trợ",
      modules: [
        { route: "/admin/support", title: "Hỗ trợ", state: "available" },
        { route: "/admin/jobs", title: "Tác vụ", state: "available" },
        { route: "/admin/payments", title: "Thanh toán", state: "available" },
        { route: "/admin/users", title: "Người dùng", state: "available" }
      ]
    }]
  }
};

const html = renderAdminWorkQueues(context);

process.stdout.write(JSON.stringify({
  hasOldTitle: html.includes("Tác vụ cần xử lý"),
  hasOldKicker: html.includes("Hàng đợi của tôi"),
  hasQuickAccessTitle: html.includes("Truy cập nhanh"),
  hasQuickAccessKicker: html.includes("Điều hướng theo quyền"),
  hasQuickAccessBody: html.includes("Mở các phân hệ được máy chủ cấp cho phiên quản trị này.")
}));
'''
    )

    assert result["hasOldTitle"] is False
    assert result["hasOldKicker"] is False
    assert result["hasQuickAccessTitle"] is True
    assert result["hasQuickAccessKicker"] is True
    assert result["hasQuickAccessBody"] is True


# ---------------------------------------------------------------------------
# 1D — Locale & Dynamic Drawer
# ---------------------------------------------------------------------------


def test_i18n_symmetric_keys_for_source_empty_and_quick_access() -> None:
    expected = {
        "vi": {
            "adminHome.sourceEmpty.title": "Chưa có số liệu vận hành",
            "adminHome.sourceEmpty.body": "Dữ liệu sẽ xuất hiện khi máy chủ cung cấp nguồn đo hợp lệ.",
            "adminHome.sourceEmpty.action": "Làm mới dữ liệu",
            "adminHome.quickAccess.kicker": "Điều hướng theo quyền",
            "adminHome.quickAccess.title": "Truy cập nhanh",
            "adminHome.quickAccess.body": "Mở các phân hệ được máy chủ cấp cho phiên quản trị này.",
        },
        "en": {
            "adminHome.sourceEmpty.title": "No operational data yet",
            "adminHome.sourceEmpty.body": "Data will appear when the server provides a valid measurement source.",
            "adminHome.sourceEmpty.action": "Refresh data",
            "adminHome.quickAccess.kicker": "Permission-aware navigation",
            "adminHome.quickAccess.title": "Quick access",
            "adminHome.quickAccess.body": "Open modules granted by the server for this admin session.",
        },
        "zh": {
            "adminHome.sourceEmpty.title": "暂无运营数据",
            "adminHome.sourceEmpty.body": "服务器提供有效的数据源后，数据将显示在这里。",
            "adminHome.sourceEmpty.action": "刷新数据",
            "adminHome.quickAccess.kicker": "按权限导航",
            "adminHome.quickAccess.title": "快速访问",
            "adminHome.quickAccess.body": "打开服务器为当前管理会话授权的模块。",
        },
    }

    blocks = _admin_home_locale_blocks()
    for lang, messages in expected.items():
        for key, value in messages.items():
            pattern = f'"{key}": "{value}"'
            assert pattern in blocks[lang], f"Missing or incorrect key {key} for lang {lang}"
            assert blocks[lang].count(f'"{key}"') == 1


def test_public_auth_language_names_and_tiny_theme_fallback_are_locale_aware() -> None:
    assert "const AUTH_LOCALE_LABELS" in PORTAL_AUTH
    assert "function authLocaleLabels" in PORTAL_AUTH
    locale_source = _between(PORTAL_AUTH, "const AUTH_LOCALE_LABELS", "function randomKey()")
    script = r'''
const fs = require("fs");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("const AUTH_LOCALE_LABELS");
const end = source.indexOf("function randomKey()", start);
if (start < 0 || end < 0) throw new Error("missing public Auth locale helper");
eval(source.slice(start, end));
process.stdout.write(JSON.stringify({ vi: authLocaleLabels("vi"), en: authLocaleLabels("en"), zh: authLocaleLabels("zh") }));
'''
    result = subprocess.run(
        ["node", "-e", script, str(PORTAL_AUTH_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "vi": [["vi", "Tiếng Việt"], ["en", "Tiếng Anh"], ["zh", "Tiếng Trung"]],
        "en": [["vi", "Vietnamese"], ["en", "English"], ["zh", "Chinese"]],
        "zh": [["vi", "越南语"], ["en", "英语"], ["zh", "中文"]],
    }
    assert "authLocaleLabels(locale)" in PORTAL_AUTH
    assert "const THEME_FALLBACK_LABELS" in THEME_JS
    assert "function interfaceLocale" in THEME_JS
    theme_harness = r'''
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync(process.argv[1], "utf8");
function run(locale) {
  const attrs = new Map([["lang", locale]]);
  const label = { textContent: "" };
  const toggle = {
    dataset: {},
    setAttribute(name, value) { this[name] = String(value); },
    querySelector(selector) {
      if (selector === "[data-portal-theme-label]") return label;
      if (selector === "[data-portal-theme-icon]") return { innerHTML: "" };
      return null;
    }
  };
  const document = {
    readyState: "complete",
    __toanAasThemeBound: false,
    documentElement: {
      style: {},
      lang: locale,
      getAttribute(name) { return attrs.get(name) || ""; },
      setAttribute(name, value) { attrs.set(name, String(value)); },
      removeAttribute(name) { attrs.delete(name); }
    },
    body: { setAttribute() {} },
    querySelector() { return null; },
    querySelectorAll(selector) { return selector === "[data-portal-theme-toggle]" ? [toggle] : []; },
    addEventListener() {}
  };
  const window = {
    location: { pathname: "/login", search: `?lang=${locale}` }, document,
    localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    matchMedia() { return { matches: false, addEventListener() {} }; },
    addEventListener() {}, dispatchEvent() {}, CustomEvent: class {}
  };
  vm.runInNewContext(source, { window, console });
  window.TOANAASPortalTheme.syncControls();
  return { label: label.textContent, aria: toggle["aria-label"] };
}
process.stdout.write(JSON.stringify({ vi: run("vi"), en: run("en"), zh: run("zh") }));
'''
    theme_result = subprocess.run(
        ["node", "-e", theme_harness, str(THEME_JS_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert theme_result.returncode == 0, theme_result.stderr
    assert json.loads(theme_result.stdout) == {
        "vi": {"label": "Giao diện: Theo hệ thống", "aria": "Giao diện: Theo hệ thống. Chuyển sang giao diện sáng"},
        "en": {"label": "Theme: System", "aria": "Theme: System. Switch to light theme"},
        "zh": {"label": "主题：跟随系统", "aria": "主题：跟随系统。切换到浅色主题"},
    }


def test_admin_login_fixed_chrome_uses_symmetric_locale_keys() -> None:
    catalogue = _between(I18N, "const MESSAGES =", "const INTERFACE_EXTENSION_MESSAGES =")
    vi = _between(catalogue, "vi: {", "en: {")
    en = _between(catalogue, "en: {", "zh: {")
    zh = catalogue[catalogue.index("zh: {") :]
    expected = {
        "vi": {
            "access.admin.action": "Đăng nhập quản trị",
            "access.admin.backCustomer": "Quay lại đăng nhập khách hàng",
            "access.admin.heading": "Đăng nhập quản trị",
            "access.admin.intro": "Cổng truy cập bảo mật dành cho quản trị viên và đội ngũ vận hành TOAN AAS.",
            "access.admin.contextLabel": "Trung tâm quản trị TOAN AAS",
            "access.admin.contextKicker": "Quản trị và vận hành",
            "access.admin.contextTitle": "Điều hành hệ thống trong phạm vi quyền được máy chủ cấp.",
            "access.admin.pointOne": "Theo dõi vận hành và xử lý công việc theo quyền.",
            "access.admin.pointTwo": "Kiểm soát đối soát và giao dịch Xu bằng dữ liệu máy chủ.",
            "access.admin.pointThree": "Phiên quản trị được xác minh và ghi nhật ký đầy đủ.",
            "access.admin.switchLabel": "Cổng quản trị và vận hành",
            "access.admin.brandSubtitle": "Trung tâm quản trị",
        },
        "en": {
            "access.admin.action": "Sign in to administration",
            "access.admin.backCustomer": "Back to customer sign-in",
            "access.admin.heading": "Administration sign-in",
            "access.admin.intro": "Secure access for TOAN AAS administrators and operations staff.",
            "access.admin.contextLabel": "TOAN AAS administration center",
            "access.admin.contextKicker": "Administration and operations",
            "access.admin.contextTitle": "Operate the system within permissions granted by the server.",
            "access.admin.pointOne": "Monitor operations and process work within your permissions.",
            "access.admin.pointTwo": "Review reconciliation and Xu transactions using server data.",
            "access.admin.pointThree": "Administrative sessions are verified and fully audited.",
            "access.admin.switchLabel": "Administration and operations portal",
            "access.admin.brandSubtitle": "Administration center",
        },
        "zh": {
            "access.admin.action": "登录管理中心",
            "access.admin.backCustomer": "返回客户登录",
            "access.admin.heading": "管理中心登录",
            "access.admin.intro": "面向 TOAN AAS 管理员和运营人员的安全访问入口。",
            "access.admin.contextLabel": "TOAN AAS 管理中心",
            "access.admin.contextKicker": "管理与运营",
            "access.admin.contextTitle": "在服务器授予的权限范围内运营系统。",
            "access.admin.pointOne": "在权限范围内监控运营并处理工作。",
            "access.admin.pointTwo": "使用服务器数据核对账务与 Xu 交易。",
            "access.admin.pointThree": "管理会话经过验证并完整记录审计日志。",
            "access.admin.switchLabel": "管理与运营入口",
            "access.admin.brandSubtitle": "管理中心",
        },
    }
    blocks = {"vi": vi, "en": en, "zh": zh}
    for locale, messages in expected.items():
        for key, value in messages.items():
            assert f'"{key}": "{value}"' in blocks[locale]
    renderer = _between(PORTAL, "function renderAuth(page, context)", "const RESULT_LABELS")
    for key in expected["vi"]:
        assert f'accessText("{key.removeprefix("access.")}"' in renderer
    for forbidden in (
        "Đăng nhập Quản trị viên",
        "Quay lại trang đăng nhập Khách hàng",
        "Cổng điều hành & Quản trị hệ thống.",
        "CỔNG QUẢN TRỊ VIÊN & VẬN HÀNH",
        'isAdminLogin ? "Admin Portal"',
    ):
        assert forbidden not in renderer


def test_set_sidebar_menu_state_uses_ui_text_without_hardcoded_labels() -> None:
    source = PORTAL_PATH.read_text(encoding="utf-8")
    fn_source = _between(source, "function setSidebarMenuState(button, opened)", "function mobileSidebarDialogSupported()")
    assert 'opened ? "Đóng điều hướng" : "Mở điều hướng"' not in fn_source
    assert 'uiText("chrome.openNavigation"' in fn_source
    assert 'uiText("chrome.closeNavigation"' in fn_source


# ---------------------------------------------------------------------------
# 1E — CSS Contract
# ---------------------------------------------------------------------------


def test_theme_css_a09_marker_and_rules() -> None:
    assert A09_CSS_MARKER in THEME, f"Missing {A09_CSS_MARKER} in portal-theme.css"
    a09_layer = THEME[THEME.index(A09_CSS_MARKER) :]

    # No 120px reservation in header
    assert "120px" not in a09_layer

    # No app switcher selectors in A09 layer
    for selector in (".portal-admin-app-switcher", ".portal-admin-app-list", ".portal-admin-app"):
        assert selector not in a09_layer, f"App switcher selector {selector} should not be in A09 layer"

    # Sidebar width 240-280px
    sidebar_match = re.search(r"grid-template-columns:\s*(2[4-8][0-9]px)\s+minmax\(0,\s*1fr\)", a09_layer)
    assert sidebar_match is not None, "A09 layer must specify grid-template-columns with 240-280px sidebar"

    # Metric grid reflow: 5 columns desktop, max 2 columns at 1279/1024/768, 1 column at 767/390/360
    assert "repeat(5, minmax(0, 1fr))" in a09_layer or "grid-template-columns: repeat(5," in a09_layer

    # Semantic tokens only in A09 layer: no raw hex (#), no rgba(, no glow, no gradient
    clean_css = re.sub(r"/\*.*?\*/", "", a09_layer, flags=re.DOTALL)
    assert "#" not in clean_css, "Raw hex colors forbidden in A09 layer"
    assert "rgba(" not in clean_css, "Raw rgba() forbidden in A09 layer"
    assert "glow" not in clean_css, "glow forbidden in A09 layer"
    assert "gradient" not in clean_css, "gradient forbidden in A09 layer"

    # Motion 150-300ms transform/opacity and reduced motion
    assert "prefers-reduced-motion" in a09_layer


def test_a09_css_uses_effective_admin_breakpoints_safe_area_and_removes_stale_rail() -> None:
    assert THEME.count(A09_CSS_MARKER) == 1
    a09 = THEME[THEME.index(A09_CSS_MARKER) :]
    admin_shell = '.portal-shell[data-portal-app-kind="admin"]:not(.portal-shell--auth):not(.portal-shell--landing)'
    desktop = _brace_body(a09, admin_shell)
    assert "grid-template-columns: 256px minmax(0, 1fr);" in desktop
    tablet = _brace_body(a09, "@media (max-width: 1279px)")
    assert f"{admin_shell} {{" not in tablet
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in tablet
    mobile = _brace_body(a09, "@media (max-width: 767px)")
    assert "grid-template-columns: minmax(0, 1fr);" in mobile
    assert "padding-inline: var(--portal-space-4);" not in mobile
    assert "var(--portal-safe-left)" in mobile
    assert "var(--portal-safe-right)" in mobile
    assert ".portal-nav-groups" not in a09
    for selector in (".portal-admin-app-switcher", ".portal-admin-app-list", ".portal-admin-app-copy"):
        assert selector not in THEME


def test_a09_admin_logo_keeps_intrinsic_ratio_when_sidebar_copy_is_long() -> None:
    a09 = THEME[THEME.index(A09_CSS_MARKER) :]
    logo = _brace_body(
        a09,
        '.portal-shell[data-portal-app-kind="admin"] .portal-sidebar .portal-brand-mark-image',
    )
    for declaration in (
        "flex: 0 0 40px;",
        "width: 100%;",
        "height: 100%;",
        "max-width: 100%;",
        "object-fit: contain;",
        "transform: none;",
    ):
        assert declaration in logo
