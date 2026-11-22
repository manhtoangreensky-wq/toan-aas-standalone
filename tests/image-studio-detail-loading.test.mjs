import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {pageMetaRenderer, pageMetaSources} from "./helpers/chat-page-meta-runtime.mjs";
import {imageStudioDetailLoadingHistoricalSource} from "./helpers/image-studio-detail-loading-historical.mjs";
import {imageStudioDetailDraftHistoricalSource} from "./helpers/image-studio-detail-draft-historical.mjs";
import {imageStudioLocaleCopyHistoricalSource} from "./helpers/image-studio-locale-copy-historical.mjs";

const contract = JSON.parse(fs.readFileSync(new URL("./fixtures/image-studio-detail-loading-contract.json", import.meta.url)));
const source = fs.readFileSync(new URL("../static/portal/integration.js", import.meta.url), "utf8").replace(/\r\n/g, "\n");
const start = source.indexOf("  function synchronizePortalHistoryNavigation() {");
const end = source.indexOf('  window.addEventListener("popstate", synchronizePortalHistoryNavigation);', start);
assert.ok(start >= 0 && end > start);
const navigation = source.slice(start, end);
const idA = "11111111-1111-4111-8111-111111111111", idB = "22222222-2222-4222-8222-222222222222";

test("physical source equals BASE plus exactly three reviewed records", () => {
  for (const record of contract.records) {
    const base = execFileSync("git", ["show", contract.base + ":" + record.file], {encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
    const current = fs.readFileSync(new URL("../" + record.file, import.meta.url), "utf8").replace(/\r\n/g, "\n");
    assert.equal(base.split(record.old).length - 1, 1);
    assert.equal(imageStudioDetailDraftHistoricalSource(imageStudioLocaleCopyHistoricalSource(current, record.file), record.file), base.replace(record.old, () => record.new));
    assert.equal(imageStudioDetailLoadingHistoricalSource(current, record.file), base);
    assert.equal(imageStudioDetailLoadingHistoricalSource(current + "\n/* unrelated */", record.file), base + "\n/* unrelated */");
    assert.throws(() => imageStudioDetailLoadingHistoricalSource(current + record.new, record.file));
  }
});

for (const locale of ["vi", "en", "zh"]) for (const family of ["/image-studio", "/image-hub"]) {
  test(`${locale} ${family}: navigation immediately shows current detail loading without stale content`, async () => {
    const render = await pageMetaRenderer(pageMetaSources()), route = family + "/" + idB;
    for (const from of ["list", "other-detail", "same-cached-target"]) {
      let state = {path: from === "other-detail" ? family + "/" + idA : family, session: {authenticated: true},
        imageStudioEnabled: true, imageStudioReadState: "ready",
        imageArtboardDetail: from === "list" ? {} : {artboard: {id: from === "same-cached-target" ? idB : idA, state: "draft", revision: 1, title: "OLD CUSTOMER"}},
        capabilities: {"image-studio-view": true}, pageStates: {"/other": "ready"}};
      let snapshot, hydrated = false;
      const box = {window: {location: {pathname: route}}, projectIdFromPath: () => "", imageArtboardIdFromPath: p => p === route ? idB : "",
        base: () => state, currentPortalPath: () => state.path, merge: patch => {state = {...state, ...patch}; snapshot = {...state};},
        hydrate: async () => {hydrated = true;}};
      vm.createContext(box);
      vm.runInContext(navigation + "\nthis.navigate=synchronizePortalHistoryNavigation;", box);
      box.navigate();
      assert.ok(hydrated);
      const view = render(locale, route, snapshot), html = view.qa.renderPage(view.page, {...view.context, ...snapshot});
      assert.match(html, /aria-busy="true"/); assert.match(html, /role="status"/); assert.match(html, /aria-live="polite"/);
      assert.doesNotMatch(html, /OLD CUSTOMER/); assert.equal(snapshot.pageStates["/other"], "ready");
      assert.ok(html.includes(view.messages[locale]["imageUi.workflow.loadingTitle"]));
      assert.ok(html.includes(view.messages[locale]["imageUi.workflow.loadingBody"]));
    }
  });

  test(`${locale} ${family}: loading, failure, access and existing form remain distinct`, async () => {
    const render = await pageMetaRenderer(pageMetaSources()), route = family + "/" + idA;
    for (const status of ["loading", "failed", "ready"]) {
      const raw = {capabilities: {"image-studio-view": true}, imageStudioEnabled: true,
        imageStudioReadState: status, imageArtboardDetail: {}, loading: true};
      const view = render(locale, route, raw), html = view.qa.renderPage(view.page, {...view.context, ...raw});
      assert.equal(/aria-busy="true"/.test(html), status === "loading");
      if (status !== "loading") assert.ok(html.includes(view.messages[locale]["imageStudioDetailUi.detail.notFoundTitle"]));
      assert.doesNotMatch(html, /data-portal-action="image-artboard-update"/);
    }
    for (const status of ["ready", "loading"]) {
      const raw = {capabilities: {"image-studio-view": true, "image-artboard-update": true}, imageStudioEnabled: true,
        imageStudioReadState: status, imageArtboardDetail: {artboard: {id: idA, state: "draft", revision: 1,
          title: "CUSTOMER <draft>"}, directions: [], versions: [], events: []}};
      const view = render(locale, route, raw), html = view.qa.renderPage(view.page, {...view.context, ...raw});
      assert.match(html, /data-portal-action="image-artboard-update"/); assert.match(html, /CUSTOMER &lt;draft&gt;/);
    }
    const denied = {capabilities: {"image-studio-view": false}, imageStudioEnabled: true,
      imageStudioReadState: "loading", imageArtboardDetail: {}};
    const view = render(locale, route, denied), html = view.qa.renderPage(view.page, {...view.context, ...denied});
    assert.doesNotMatch(html, /aria-busy="true"/); assert.doesNotMatch(html, /data-portal-action="image-artboard-update"/);
  });
}
