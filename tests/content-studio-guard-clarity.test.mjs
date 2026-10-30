import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const start = source.indexOf("  function renderContentStudio(page, context)");
const end = source.indexOf("\n  function renderContentStudioDetail", start);
assert.ok(start >= 0 && end > start, "renderContentStudio boundary must remain present");

function render(readState, capabilities = {}) {
  const context = {
    safeText: value => String(value ?? ""),
    ICONS: { prompt: "✦" },
    renderHero: () => "<header>Nội dung</header>",
    contentStudioText: (_key, fallback) => fallback,
    transientFormValues: () => ({}),
    document: {}
  };
  vm.createContext(context);
  vm.runInContext(`${source.slice(start, end)}\nglobalThis.renderContentStudio = renderContentStudio;`, context);
  return context.renderContentStudio(
    { path: "/content-studio", routePath: "/content-studio" },
    { path: "/content-studio", capabilities, contentStudioReadState: readState }
  );
}

test("Content Studio guarded states keep the action message without technical chips", () => {
  for (const [state, expected] of [
    ["guarded", "Nội dung sáng tạo đang được bảo vệ"],
    ["loading", "Đang xác minh không gian nội dung riêng tư"],
    ["failed", "Chưa thể tải không gian nội dung riêng tư"]
  ]) {
    const html = render(
      state,
      state === "guarded"
        ? {}
        : { "content-studio-view": true, ...(state === "failed" ? { "content-studio-refresh": true } : {}) }
    );
    assert.match(html, new RegExp(expected));
    assert.doesNotMatch(html, /portal-state-meta/);
    assert.doesNotMatch(html, /Phiên đã xác minh|Không dùng bộ nhớ cũ|Không có cầu nối dự phòng/);
  }
});
