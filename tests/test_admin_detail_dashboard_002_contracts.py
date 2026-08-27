"""Contracts for the snapshot-only Admin detail dashboard."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PORTAL_PATH = ROOT / "static/portal/portal.js"
PORTAL = PORTAL_PATH.read_text(encoding="utf-8")
I18N = (ROOT / "static/portal/portal-i18n.js").read_text(encoding="utf-8")
THEME = (ROOT / "static/portal/portal-theme.css").read_text(encoding="utf-8")
DASHBOARD_CSS_MARKER = "/* Admin Detail Dashboard 002 ----------------------------------------- */"


def _between(source: str, start: str, end: str) -> str:
    offset = source.index(start)
    return source[offset : source.index(end, offset + len(start))]


def _run_dashboard(body: str) -> dict[str, object]:
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
function safeText(value) { return String(value); }
const messages = {
  "analytics.title": "Phân tích vận hành",
  "analytics.description": "Ảnh chụp hiện tại từ dữ liệu máy chủ; không phải xu hướng theo thời gian.",
  "workload.title": "Khối lượng vận hành",
  "workload.description": "So sánh ba số liệu trong ảnh chụp hiện tại.",
  "workload.empty": "Chưa có số liệu vận hành",
  "readinessChart.title": "Mức sẵn sàng",
  "readinessChart.description": "Tỷ lệ trạng thái sẵn sàng trong ảnh chụp hiện tại.",
  "readinessChart.ready": "Sẵn sàng",
  "readinessChart.guarded": "Cần kiểm tra",
  "readinessChart.empty": "Chưa có dữ liệu sẵn sàng",
  "readinessChart.aria": "Mức sẵn sàng: {ready} sẵn sàng, {guarded} cần kiểm tra trên tổng số {total}.",
  "connectionDetails.title": "Chi tiết kết nối",
  "metrics.engineJobs": "Tác vụ hệ thống",
  "metrics.workerJobs": "Tác vụ xử lý",
  "metrics.payments": "Thanh toán"
};
function adminText(key, fallback, params) {
  let value = messages[key] || fallback;
  Object.entries(params || {}).forEach(([name, replacement]) => {
    value = value.replaceAll(`{${name}}`, String(replacement));
  });
  return value;
}
function uiText(key, fallback, params) {
  return adminText(key.replace(/^adminHome\./, ""), fallback, params);
}
eval(extract("function adminDashboardNumber", "function renderAdminOverview(page, context)"));
''' + body
    result = subprocess.run(
        ["node", "-e", script, str(PORTAL_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_workload_snapshot_uses_exact_counts_and_normalized_widths() -> None:
    result = _run_dashboard(
        r'''
const counts = { engine_jobs: 12, worker_jobs: 7, payments: 42 };
const model = adminDashboardWorkloadRows(counts, adminText);
const html = renderAdminDashboardAnalytics({ counts, readiness: {} }, adminText);
process.stdout.write(JSON.stringify({
  labels: model.rows.map((row) => row.label),
  values: model.rows.map((row) => row.value),
  widths: model.rows.map((row) => row.width),
  barCount: (html.match(/class="portal-admin-workload-bar-fill"/g) || []).length,
  styles: Array.from(html.matchAll(/--portal-admin-bar-width: ([0-9.]+)%/g), (match) => Number(match[1])),
  hasValues: [12, 7, 42].every((value) => html.includes(`<strong>${value}</strong>`))
}));
'''
    )

    assert result == {
        "labels": ["Tác vụ hệ thống", "Tác vụ xử lý", "Thanh toán"],
        "values": [12, 7, 42],
        "widths": [28.57, 16.67, 100],
        "barCount": 3,
        "styles": [28.57, 16.67, 100],
        "hasValues": True,
    }


def test_readiness_snapshot_uses_real_entries_and_has_honest_empty_state() -> None:
    result = _run_dashboard(
        r'''
const readiness = {
  image: { public_ready: true, adapter: "image-local" },
  video: { public_ready: true, adapter: "video-local" },
  audio: { public_ready: false, adapter: "audio-guarded" }
};
const model = adminDashboardReadinessSnapshot(readiness);
const readyHtml = renderAdminDashboardAnalytics({ counts: { engine_jobs: 12, worker_jobs: 7, payments: 42 }, readiness }, adminText);
const emptyHtml = renderAdminDashboardAnalytics({ counts: {}, readiness: {} }, adminText);
process.stdout.write(JSON.stringify({
  model,
  angle: Number((readyHtml.match(/--portal-admin-ready-angle: ([0-9.]+)deg/) || [])[1]),
  showsPercent: readyHtml.includes("<strong>67%</strong>"),
  readyLegend: readyHtml.includes("<dt>Sẵn sàng</dt><dd>2</dd>"),
  guardedLegend: readyHtml.includes("<dt>Cần kiểm tra</dt><dd>1</dd>"),
  roleAndAria: readyHtml.includes('role="img"') && readyHtml.includes('aria-label="Mức sẵn sàng: 2 sẵn sàng, 1 cần kiểm tra trên tổng số 3."'),
  noInventedGraphic: !readyHtml.includes("<svg") && !readyHtml.includes("<path"),
  emptyText: emptyHtml.includes("Chưa có số liệu vận hành") && emptyHtml.includes("Chưa có dữ liệu sẵn sàng"),
  emptyHasDonut: emptyHtml.includes("portal-admin-readiness-donut"),
  emptyHasFill: emptyHtml.includes("portal-admin-workload-bar-fill")
}));
'''
    )

    assert result == {
        "model": {"total": 3, "ready": 2, "guarded": 1, "percent": 67, "angle": 241.2},
        "angle": 241.2,
        "showsPercent": True,
        "readyLegend": True,
        "guardedLegend": True,
        "roleAndAria": True,
        "noInventedGraphic": True,
        "emptyText": True,
        "emptyHasDonut": False,
        "emptyHasFill": False,
    }


def test_overview_places_analytics_before_queues_and_keeps_every_connection() -> None:
    result = _run_dashboard(
        r'''
function adminErpNavigation(context) { return context.navigation; }
const ICONS = { security: "security" };
function portalIcon() { return "icon"; }
function badge(state) { return ["ready", "guarded", "read_only"].includes(state) ? "" : `<span>${state}</span>`; }
function renderSummary() { return "summary"; }
function renderRowsTable(headers, rows, rowRenderer) {
  return `<table data-row-count="${rows.length}"><thead><tr>${headers.map((header) => `<th>${header}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${rowRenderer(row)}</tr>`).join("")}</tbody></table>`;
}
function renderAdminWorkQueues() { return '<section data-work-queues></section>'; }
function renderAdminDirectory() { return '<section data-directory></section>'; }
eval(extract("function renderAdminOverview(page, context)", "function renderAdminSystemStewardship(page, context)"));
const readiness = Object.fromEntries(Array.from({ length: 10 }, (_, index) => [
  `feature-${index + 1}`,
  { public_ready: index % 2 === 0, adapter: `connection-${index + 1}` }
]));
const html = renderAdminOverview({}, {
  adminData: { counts: { users: 1284, engine_jobs: 12, worker_jobs: 7, payments: 42 }, readiness },
  navigation: { canonicalAdmin: true, webLocalAdmin: false, supportRole: "none" },
  capabilities: { "refresh-admin": true }
});
process.stdout.write(JSON.stringify({
  rowCount: Number((html.match(/data-row-count="([0-9]+)"/) || [])[1]),
  lastAdapter: html.includes("connection-10"),
  analyticsBeforeQueues: html.indexOf("portal-admin-dashboard-analytics") < html.indexOf("data-work-queues"),
  title: html.includes("Chi tiết kết nối"),
  ordinalHeader: html.includes("<th>STT</th>"),
  firstOrdinal: html.includes("<tr><td>1</td><td>feature-1</td>"),
  lastOrdinal: html.includes("<tr><td>10</td><td>feature-10</td>"),
  readyStatus: html.includes('<span class="portal-admin-data-status" data-status="ready">Sẵn sàng</span>'),
  guardedStatus: html.includes('<span class="portal-admin-data-status" data-status="guarded">Cần kiểm tra</span>'),
  refresh: html.includes('data-portal-action="refresh-admin"')
}));
'''
    )

    assert result == {
        "rowCount": 10,
        "lastAdapter": True,
        "analyticsBeforeQueues": True,
        "title": True,
        "ordinalHeader": True,
        "firstOrdinal": True,
        "lastOrdinal": True,
        "readyStatus": True,
        "guardedStatus": True,
        "refresh": True,
    }


def test_locale_keys_are_symmetric_exact_and_new_vietnamese_copy_is_clean() -> None:
    catalogue = _between(I18N, "const ADMIN_HOME_MESSAGES =", "const ADMIN_DATA_SURFACE_MESSAGES =")
    vi = _between(catalogue, "vi: {", "en: {")
    en = _between(catalogue, "en: {", "zh: {")
    expected = {
        "adminHome.analytics.title": ("Phân tích vận hành", "Operations analysis"),
        "adminHome.analytics.description": ("Ảnh chụp hiện tại từ dữ liệu máy chủ; không phải xu hướng theo thời gian.", "Current server-data snapshot; this is not a time-series trend."),
        "adminHome.workload.title": ("Khối lượng vận hành", "Operations workload"),
        "adminHome.workload.empty": ("Chưa có số liệu vận hành", "No operations data"),
        "adminHome.readinessChart.title": ("Mức sẵn sàng", "Readiness"),
        "adminHome.readinessChart.ready": ("Sẵn sàng", "Ready"),
        "adminHome.readinessChart.guarded": ("Cần kiểm tra", "Needs review"),
        "adminHome.readinessChart.empty": ("Chưa có dữ liệu sẵn sàng", "No readiness data"),
        "adminHome.connectionDetails.title": ("Chi tiết kết nối", "Connection details"),
        "adminHome.readiness.table.ordinal": ("STT", "No."),
    }
    for key, (vi_value, en_value) in expected.items():
        assert f'"{key}": "{vi_value}"' in vi
        assert f'"{key}": "{en_value}"' in en
        assert catalogue.count(f'"{key}"') == 3

    helpers = _between(PORTAL, "function adminDashboardNumber", "function renderAdminOverview(page, context)")
    forbidden = ("Job", "readiness", "adapter", "provider", "signed session", "canonical", "Core Bridge")
    fallbacks = re.findall(r'adminText\("[^"]+",\s*"([^"]+)"', helpers)
    assert not [value for value in fallbacks for token in forbidden if re.search(rf"\b{re.escape(token)}\b", value, re.I)]


def test_dashboard_css_is_scoped_responsive_static_and_uses_one_data_gradient() -> None:
    block = THEME[THEME.index(DASHBOARD_CSS_MARKER) :]
    root = '.portal-shell[data-portal-app-kind="admin"] .portal-admin-dashboard-analytics'
    donut_selector = f"{root} .portal-admin-readiness-donut"
    donut_rule = re.search(re.escape(donut_selector) + r"\s*\{([^{}]*)\}", block)
    assert donut_rule, donut_selector
    assert "background: conic-gradient(var(--portal-action) 0 var(--portal-admin-ready-angle), var(--portal-border) var(--portal-admin-ready-angle) 360deg);" in donut_rule.group(1)
    assert "--portal-admin-readiness-background" not in block
    assert "background: var(--portal-admin-readiness-background);" not in block
    for contract in (
        f"{root} {{",
        "grid-template-columns: minmax(0, 1.25fr) minmax(280px, .75fr);",
        "height: 12px;",
        "width: var(--portal-admin-bar-width);",
        "width: 144px;",
        "width: 128px;",
        "font-size: 16px;",
        "line-height: 1.5;",
        "@media (max-width: 760px)",
        "@media (max-width: 700px)",
    ):
        assert contract in block
    assert block.count("conic-gradient(") == 1
    assert "linear-gradient(" not in block and "radial-gradient(" not in block
    assert not re.search(r"#[0-9a-fA-F]{3,8}|rgba?\(", block)
    assert all(token not in block for token in ("glow", "!important", "@keyframes", "animation:", "transition:"))
