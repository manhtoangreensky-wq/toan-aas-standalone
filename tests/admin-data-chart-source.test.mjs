import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const portal = fs.readFileSync("static/portal/portal.js", "utf8");
const css = fs.readFileSync("static/portal/portal-theme.css", "utf8");
const i18n = fs.readFileSync("static/portal/portal-i18n.js", "utf8");

function section(startMarker, endMarker) {
  const start = portal.indexOf(startMarker);
  const end = portal.indexOf(endMarker, start + startMarker.length);
  assert.ok(start >= 0 && end > start, `missing source section: ${startMarker}`);
  return portal.slice(start, end);
}

const chartSource = section("function adminDataChartProjection", "const ADMIN_DATA_VIEW_ROUTE_KEYS");

function chartHelpers() {
  const factory = new Function(`
    function safeText(value) {
      return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
    }
    function adminNumericValue(value) {
      if (typeof value === "number") return Number.isFinite(value) ? value : null;
      if (typeof value !== "string" || !value.trim()) return null;
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    }
    function localizedNumber(value) { return Number(value).toLocaleString("vi-VN"); }
    function adminDataViewText(key, fallback) {
      return key === "chartLegend" ? "Chú giải" : fallback;
    }
    ${chartSource}
    return { adminDataChartProjection, renderAdminDataChart };
  `);
  return factory();
}

test("Admin dynamic chart accepts only bounded server-issued read data", () => {
  const { adminDataChartProjection } = chartHelpers();
  const chart = adminDataChartProjection({
    chart: {
      title: "Tình trạng tác vụ",
      description: "Ảnh chụp hiện tại",
      unit: "tác vụ",
      points: [{ label: "Đang xử lý", value: 2 }, { label: "Hoàn tất", value: 4 }],
      legend: [{ label: "Đã cấp", tone: "success" }]
    }
  });
  assert.deepEqual(chart.points.map((point) => point.width), [50, 100]);
  assert.equal(chart.legend[0].tone, "success");
  assert.equal(adminDataChartProjection({ compatibility_guarded: true, chart: { title: "Không được hiện", points: [{ label: "A", value: 1 }] } }), null);
  assert.equal(adminDataChartProjection({ chart: { title: "Sai", points: [{ label: "A", value: -1 }] } }), null);
  assert.equal(adminDataChartProjection({ chart: { title: "Sai", points: [{ label: "A", value: 1 }], legend: [{ label: "A", tone: "rainbow" }] } }), null);
});

test("Admin dynamic chart renders accessible bars and legend without a write action", () => {
  const { renderAdminDataChart } = chartHelpers();
  const html = renderAdminDataChart("jobs", {
    chart: {
      title: "Tình trạng tác vụ",
      description: "Ảnh chụp hiện tại",
      unit: "tác vụ",
      points: [{ label: "Đang xử lý", value: 2 }, { label: "Hoàn tất", value: 4 }],
      legend: [{ label: "Đã cấp", tone: "success" }]
    }
  });
  assert.match(html, /<figure class="portal-admin-data-chart"/);
  assert.match(html, /aria-labelledby="admin-data-jobs-chart-title"/);
  assert.match(html, /role="img" aria-label="Đang xử lý: 2 tác vụ"/);
  assert.match(html, /portal-admin-data-chart-key--success/);
  assert.doesNotMatch(html, /data-portal-action|fetch\(|XMLHttpRequest|wallet|payos|provider/i);
  assert.equal(renderAdminDataChart("jobs", { items: [] }), "");
});

test("Admin data surface wires the optional chart and keeps locale coverage balanced", () => {
  const surface = section("function renderAdminDataSurface", "function adminJobActions");
  assert.match(surface, /renderAdminDataChart\(module, source\)/);
  for (const key of ["chartKicker", "chartLegend"]) {
    assert.equal((i18n.match(new RegExp(`\\"adminDataView\\.${key}\\"`, "g")) || []).length, 3, `${key} must exist in VI/EN/ZH`);
  }
  const marker = "/* Admin Data Views 003 ---------------------------------------------- */";
  const cssStart = css.indexOf(marker);
  const cssEnd = css.indexOf("/* Admin Detail Dashboard 002 Layout", cssStart);
  assert.ok(cssStart >= 0, "admin data chart CSS marker must exist");
  assert.ok(cssEnd > cssStart, "admin data chart CSS layer must end before the next admin section");
  const cssLayer = css.slice(cssStart, cssEnd);
  for (const token of [
    ".portal-admin-data-chart",
    ".portal-admin-data-chart-point-meta",
    ".portal-admin-data-chart-track",
    ".portal-admin-data-chart-legend",
    "var(--portal-action)",
    "var(--portal-surface-light)"
  ]) assert.ok(cssLayer.includes(token), `missing chart style token: ${token}`);
  assert.doesNotMatch(cssLayer, /transition:|animation:|gradient|fetch\(|data-portal-action/);
});
