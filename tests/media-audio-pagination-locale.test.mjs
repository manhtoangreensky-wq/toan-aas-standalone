import test from "node:test";
import assert from "node:assert/strict";
import {execFileSync} from "node:child_process";
import path from "node:path";
import {runtime, sources, context, collection, hash, ROOT} from "./helpers/media-collection-locale-runtime.mjs";

// Contracted customer output, independently specified before the application patch.
const BASE = "051b936695638a5f083396194730861dc7831da1";
const COPY = Object.freeze({
  vi: {label: "tệp âm thanh", range: "Đang hiển thị 51–53 tệp âm thanh",
    empty: "Không có tệp âm thanh ở trang này", aria: "Phân trang tệp âm thanh",
    previous: "← Trang trước", next: "Trang sau →"},
  en: {label: "audio files", range: "Showing 51–53 audio files",
    empty: "No audio files on this page", aria: "audio files pagination",
    previous: "← Previous", next: "Next →"},
  zh: {label: "音频文件", range: "正在显示第 51–53 个音频文件",
    empty: "此页没有音频文件", aria: "音频文件分页",
    previous: "← 上一页", next: "下一页 →"}
});
const current = sources();
const raw = Object.fromEntries([["portal", "static/portal/portal.js"], ["i18n", "static/portal/portal-i18n.js"]]
  .map(([key, file]) => [key, execFileSync("git", ["show", BASE + ":" + file],
    {cwd: ROOT, encoding: "utf8", maxBuffer: 30e6, windowsHide: true})]));
const baseline = {raw, paths: Object.fromEntries(Object.keys(raw).map(key =>
  [key, path.join(ROOT, key === "portal" ? "static/portal/portal.js" : "static/portal/portal-i18n.js")])),
  hashes: Object.fromEntries(Object.entries(raw).map(([key, value]) => [key, hash(value)])), baseline: true};
const listing = (returned = 3, more = true) => ({filters: {q: ""},
  pagination: {limit: 50, offset: 50, returned, previous_offset: 0, has_more: more, next_offset: more ? 100 : null}});
const ownNav = html => {
  const found = html.match(/<nav class="portal-media-pagination"[^>]*>[\s\S]*?<\/nav>/g) || [];
  assert.equal(found.length, 1, "The actual audio detail owns one audio pager");
  return found[0];
};

test("physical binding: complete current bundles execute with one observation exposure and no replaced production functions", () => {
  const r = runtime(current, "vi");
  assert.equal(r.binding.exposureCount, 1);
  assert.equal(r.binding.replacedProductionFunctions, 0);
  assert.deepEqual(r.attempts(), []);
});

for (const locale of ["vi", "en", "zh"]) {
  for (const root of ["/media-workspace", "/audio-hub"]) {
    for (const empty of [false, true]) {
      test(`${locale}${root}/${empty ? "empty" : "range"}: real detail renders localized audio pager without changing action route or offset`, () => {
        const r = runtime(current, locale), row = collection(), route = root + "/" + row.id;
        const page = r.page(route), ctx = context({row, overrides: {path: route, interfaceLocale: locale,
          mediaAudioAssetFilter: {q: ""}, mediaAudioAssetListing: listing(empty ? 0 : 3, !empty)}});
        const html = r.call("renderMediaWorkspaceDetail", page, ctx), nav = ownNav(html), want = COPY[locale];
        assert.ok(nav.includes(empty ? want.empty : want.range), "Locale-specific customer range/empty copy: " + nav);
        assert.ok(nav.includes('aria-label="' + want.aria + '"'));
        assert.ok(nav.includes(">" + want.previous + "</button>"));
        assert.equal(nav.includes(">" + want.next + "</button>"), !empty);
        assert.ok(nav.includes('data-portal-action="media-audio-page"'));
        assert.ok(nav.includes('data-portal-route="' + route + '"'));
        assert.ok(nav.includes('data-media-audio-offset="0"'));
        assert.equal(nav.includes('data-media-audio-offset="100"'), !empty);
        assert.ok(!nav.includes("Asset Vault"));
        assert.ok(html.includes("Facebook TikTok"), "Customer-supplied title remains visible");
        assert.deepEqual(r.attempts(), []);
      });
    }
  }
  test(`${locale}: exact non-audio paginator tuples and malformed lookalikes preserve full BASE output`, () => {
    const r = runtime(current, locale), b = runtime(baseline, locale);
    const tuples = [
      ["ghi chú", "memory-note-page", "/notes", "data-memory-note-offset", undefined],
      ["lời nhắc", "memory-reminder-page", "/reminders", "data-memory-reminder-offset", "portal-memory-pagination"],
      ["template", "prompt-library-page", "/prompt-library", "data-prompt-library-offset", "portal-prompt-library-pagination"],
      ["audio collection", "media-workspace-page", "/media-workspace", "data-media-collection-offset", "portal-media-pagination"],
      ["nhạc", "music-library-page", "/music/library", "data-music-library-offset", "portal-music-library-pagination"],
      ["artboard", "image-studio-page", "/image-studio", "data-image-studio-offset", "portal-image-studio-pagination"],
      ["tham chiếu dự án", "image-studio-project-reference-page", "/image-studio/owned-id", "data-image-studio-project-reference-offset", "portal-image-reference-pagination"],
      ["tham chiếu ảnh", "image-studio-asset-reference-page", "/image-hub/owned-id", "data-image-studio-asset-reference-offset", "portal-image-reference-pagination"],
      ["document brief", "document-workspace-page", "/document-workspace", "data-document-workspace-offset", "portal-document-workspace-pagination"],
      ["Inbox", "inbox-page", "/inbox", "data-inbox-offset", "portal-inbox-pagination"],
      ["CUSTOMER <em> & Facebook", "unknown-action", "/media-workspace", "data-custom-offset", "portal-media-pagination"],
      ["CUSTOMER", "media-audio-page", "/custom", "data-custom-offset", "portal-custom-pagination"]
    ];
    for (const tuple of tuples) for (const rows of [listing(), listing(0, false)]) {
      assert.equal(r.call("renderMemoryPagination", rows, ...tuple),
        b.call("renderMemoryPagination", rows, ...tuple), JSON.stringify(tuple));
    }
  });
  test(`${locale}: no previous or next page yields no empty navigation container`, () => {
    const r = runtime(current, locale);
    const noPages = {pagination: {limit: 50, offset: 0, returned: 0, has_more: false, next_offset: null, previous_offset: null}};
    assert.equal(r.call("renderMemoryPagination", noPages, COPY[locale].label, "media-audio-page",
      "/audio-hub/owned-id", "data-media-audio-offset", "portal-media-pagination"), "");
  });
}
