import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const start = source.indexOf("  function renderProjectCenter(page, context)");
const end = source.indexOf("\n  function renderMemoryTagList", start);
assert.ok(start >= 0 && end > start, "renderProjectCenter boundary must remain present");

function render(readState, capabilities = {}) {
  const context = {
    safeText: value => String(value ?? ""),
    portalIcon: () => "⌂",
    ICONS: { dashboard: "dashboard", refresh: "refresh", shield: "shield" },
    renderHero: () => "<header>Project</header>",
    projectCenterText: (_key, fallback) => fallback,
    projectCenterReadState: value => value?.projectsReadState || "guarded",
    document: {}
  };
  vm.createContext(context);
  vm.runInContext(`${source.slice(start, end)}\nglobalThis.renderProjectCenter = renderProjectCenter;`, context);
  return context.renderProjectCenter(
    { path: "/projects", routePath: "/projects" },
    { path: "/projects", capabilities, projectsReadState: readState }
  );
}

test("Project Center guarded states keep the action message without technical chips", () => {
  for (const [state, expected] of [
    ["guarded", "Bảng vận hành dự án đang được bảo vệ"],
    ["loading", "Đang xác minh dự án riêng tư"],
    ["failed", "Chưa thể tải dự án riêng tư"]
  ]) {
    const html = render(state, state === "guarded" ? {} : { "projects-refresh": true });
    assert.match(html, new RegExp(expected));
    assert.doesNotMatch(html, /portal-state-meta/);
    assert.doesNotMatch(html, /Phiên đã xác thực|Không dùng bộ nhớ đệm riêng tư|Không có dữ liệu cũ/);
  }
});
