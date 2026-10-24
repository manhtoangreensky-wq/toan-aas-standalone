import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const start = source.indexOf("  function renderCampaignPlanner(page, context)");
const end = source.indexOf("\n  function renderCampaignDetail", start);
assert.ok(start >= 0 && end > start, "renderCampaignPlanner boundary must remain present");

function render(state, session, capabilities = {}) {
  const context = {
    safeText: value => String(value ?? ""),
    portalIcon: () => "⌂",
    ICONS: { dashboard: "dashboard", refresh: "refresh", shield: "shield", prompt: "prompt" },
    renderHero: () => "<header>Kế hoạch</header>",
    campaignText: (_key, fallback) => fallback,
    campaignPlannerReadState: value => value?.campaignPlannerReadState || "guarded",
    document: {}
  };
  vm.createContext(context);
  vm.runInContext(`${source.slice(start, end)}\nglobalThis.renderCampaignPlanner = renderCampaignPlanner;`, context);
  return context.renderCampaignPlanner(
    { path: "/campaigns", routePath: "/campaigns" },
    { path: "/campaigns", session, capabilities, campaignPlannerReadState: state }
  );
}

test("Campaign Planner guarded states keep the action message without technical chips", () => {
  const cases = [
    ["guarded", { authenticated: false }, {}, "Bảng kế hoạch đang được bảo vệ"],
    ["loading", { authenticated: true }, { "campaigns-refresh": true }, "Đang xác minh kế hoạch riêng"],
    ["failed", { authenticated: true }, { "campaigns-refresh": true }, "Chưa thể tải kế hoạch riêng"]
  ];
  for (const [state, session, capabilities, expected] of cases) {
    const html = render(state, session, capabilities);
    assert.match(html, new RegExp(expected));
    assert.doesNotMatch(html, /portal-state-meta/);
    assert.doesNotMatch(html, /Phạm vi tài khoản|Không dùng bộ nhớ cũ|Không có dữ liệu cũ/);
  }
});
