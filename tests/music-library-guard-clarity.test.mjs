import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync("static/portal/portal.js", "utf8").replace(/\r\n/g, "\n");
const start = source.indexOf("  function renderMusicLibrary(");
const end = source.indexOf("\n  function mediaAudioAssetFilterFields", start);
assert.ok(start >= 0 && end > start, "renderMusicLibrary boundary must remain present");

function render() {
  const context = {
    safeText: value => String(value ?? ""),
    portalIcon: () => "♪",
    ICONS: { music: "music" },
    renderHero: () => "<header>Âm thanh</header>",
    renderFields: () => "",
    renderEmpty: () => "",
    renderMemoryPagination: () => "",
    musicLibraryRoleForPage: () => "music",
    musicLibraryText: (_key, fallback) => fallback,
    musicLibraryListing: () => ({ filters: { q: "" } }),
    musicLibraryItems: () => [],
    mediaCollectionTags: () => [],
    document: {}
  };
  vm.createContext(context);
  vm.runInContext(`${source.slice(start, end)}\nglobalThis.renderMusicLibrary = renderMusicLibrary;`, context);
  return context.renderMusicLibrary(
    { path: "/music/library", routePath: "/music/library" },
    { path: "/music/library", capabilities: {}, musicLibraryReadState: "guarded" }
  );
}

test("music library guard keeps one useful message instead of technical status chips", () => {
  const html = render();
  assert.match(html, /Bạn cần đăng nhập và được cấp quyền truy cập thư viện âm thanh/);
  assert.match(html, /data-portal-action="music-library-refresh"/);
  assert.match(html, /href="\/music\/sfx-library"/);
  assert.doesNotMatch(html, /portal-state-meta/);
  assert.doesNotMatch(html, /Thông tin riêng tư|Chưa hỗ trợ nghe thử|Chưa hỗ trợ tải tệp/);
});
