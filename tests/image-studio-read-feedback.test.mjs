import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {imageStudioReadFeedbackHistoricalSource, imageStudioReadFeedbackHistoricalSnapshot} from "./helpers/image-studio-read-feedback-historical.mjs";
import {imageStudioDetailLoadingHistoricalSource} from "./helpers/image-studio-detail-loading-historical.mjs";

const root = new URL("../", import.meta.url);
const contract = JSON.parse(fs.readFileSync(new URL("fixtures/image-studio-read-feedback-contract.json", import.meta.url)));
const read = file => fs.readFileSync(new URL(file, root), "utf8").replace(/\r\n/g, "\n");
const prior = file => execFileSync("git", ["show", contract.base + ":" + file], {cwd: root, encoding: "utf8", maxBuffer: 30e6}).replace(/\r\n/g, "\n");
const source = read("static/portal/integration.js"), catalogue = read("static/portal/portal-i18n.js");
const between = (start, end) => {
  const i = source.indexOf(start), j = source.indexOf(end, i + start.length);
  assert.ok(i >= 0 && j > i);
  return source.slice(i, j);
};
const functions = between("  function imageStudioRequestIsCurrent(", "  function isNativeImagePromptComposerPath(")
  + between("  function imageStudioReadFeedbackText(", "  async function hydrateImageStudio(")
  + between("  async function hydrateImageStudio(", "  async function hydrateImageStudioReferences(")
  + between("  async function hydrateImageArtboard(", "  const CHAT_WORKSPACE_LIST_LIMIT");
const actions = between('      if (action === "image-studio-filter") {', '      if (["image-studio-project-reference-filter"')
  + between('      if (action === "image-studio-refresh") {', '      if (action === "image-artboard-create") {');
const messages = {
  vi: {refreshed: "Đã làm mới.", filtered: "Đã áp dụng bộ lọc.", listed: "Đã tải danh sách.", paged: "Đã tải trang.", failed: "Không thể tải dữ liệu. Vui lòng thử lại."},
  en: {refreshed: "Refreshed.", filtered: "Filter applied.", listed: "List loaded.", paged: "Page loaded.", failed: "Could not load the data. Please try again."},
  zh: {refreshed: "已刷新。", filtered: "已应用筛选。", listed: "列表已加载。", paged: "页面已加载。", failed: "无法加载数据，请重试。"}
};
function dictionary(locale) {
  const noop = () => {};
  const document = {readyState: "loading", addEventListener: noop, querySelector: () => null, querySelectorAll: () => [],
    documentElement: {lang: locale, setAttribute: noop, getAttribute: () => null, classList: {add: noop, remove: noop}}, body: {setAttribute: noop}};
  const window = {document, navigator: {language: locale}, location: {pathname: "/image-studio", search: ""},
    addEventListener: noop, dispatchEvent: noop, localStorage: {getItem: () => null, setItem: noop}};
  const context = vm.createContext({window, document, navigator: window.navigator, location: window.location, URL, URLSearchParams, Intl, console});
  vm.runInContext(catalogue, context);
  window.TOANAASI18n.setLocale(locale, {emit: false});
  return window.TOANAASI18n;
}
function harness(kind, action, locale, api, extra = {}) {
  const id = "11111111-1111-4111-8111-111111111111", route = kind === "detail" ? "/image-studio/" + id : "/image-studio", logs = [];
  const box = {route, action, fields: {q: "x", state: "active", __imageStudioOffset: 0}, logs,
    imageStudioSessionEpoch: 1, imageStudioHydrationEpoch: 0, imageStudioDetailHydrationEpoch: 0,
    IMAGE_STUDIO_ARTBOARD_LIST_LIMIT: 50, window: {TOANAASI18n: dictionary(locale)}};
  box.state = {session: {authenticated: true}, capabilities: {"image-studio-filter": true, "image-studio-page": true},
    imageStudioEnabled: true, imageStudioReferences: {}, imageStudioListing: {}, pageStates: {}};
  Object.assign(box, {base: () => box.state, currentPortalPath: () => box.route, isNativeImageStudioPath: p => p.startsWith("/image-studio"),
    validImageStudioArtboardId: value => value === id, validImageStudioRevision: () => true,
    imageStudioReferenceRequestState: refs => {if (refs.invalid) throw Error("specific validation error"); return {filter: {q: ""}, offset: 0};},
    imageStudioArtboardFilterPayload: value => {if (value.q === "invalid") throw Error("invalid filter"); return value;},
    imageStudioListOffset: value => Number(value || 0), imageStudioArtboardListPath: () => "/boards",
    imageStudioReferenceListPath: key => "/references/" + key, imageStudioBoundaryIsSafe: () => true,
    imageStudioReferenceStateWithPage: value => value, imageStudioReferencesWithPinned: value => value,
    imageStudioListingProjection: () => ({}), imageStudioArtboardRoute: (_id, value) => value,
    imageArtboardIdFromPath: value => value.endsWith(id) ? id : "", merge: value => {box.state = {...box.state, ...value};},
    toast: (message, type) => logs.push({message, type: type || "success"}), ...extra});
  box.api = url => api(box, url, id);
  vm.createContext(box);
  vm.runInContext(functions + "\nasync function invoke(){" + actions + "}\nthis.invoke=invoke;this.readWithFeedback=imageStudioReadWithFeedback;", box);
  return box;
}

test("physical source is exactly the six reviewed records and historical inverse is bounded", () => {
  assert.equal(contract.records.length, 6);
  for (const file of ["static/portal/integration.js", "static/portal/portal-i18n.js"]) {
    let expected = prior(file);
    for (const row of contract.records.filter(row => row.file === file)) {
      assert.equal(expected.split(row.old).length - 1, 1);
      expected = expected.replace(row.old, () => row.new);
    }
    assert.equal(imageStudioDetailLoadingHistoricalSource(read(file), file), expected);
    assert.equal(imageStudioReadFeedbackHistoricalSource(expected, file), prior(file));
    assert.equal(imageStudioReadFeedbackHistoricalSource(expected + "\n/* unrelated */", file), prior(file) + "\n/* unrelated */");
  }
  const mixed = source.replace(contract.records[1].new, contract.records[1].old);
  assert.throws(() => imageStudioReadFeedbackHistoricalSource(mixed, "static/portal/integration.js"));
});

for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}: current success, empty result, failure and stale replies give truthful feedback`, async () => {
    const all = [];
    for (const kind of ["list", "detail"]) for (const action of kind === "list"
      ? ["image-studio-refresh", "image-studio-filter", "image-studio-filter-clear", "image-studio-page"] : ["image-studio-refresh"])
      for (const scenario of ["success", "failed", "staleRoute", "logout", "newer"]) {
        const box = harness(kind, action, locale, async (context, url, id) => {
          await Promise.resolve();
          if (scenario === "staleRoute") context.route = "/other";
          if (scenario === "logout") context.state.session = {authenticated: false};
          if (scenario === "newer") context[kind === "detail" ? "imageStudioDetailHydrationEpoch" : "imageStudioHydrationEpoch"]++;
          if (scenario === "failed") throw Error("controlled failure");
          return {data: url.endsWith(id) ? {artboard: {id, state: "archived", revision: 1}, directions: [], versions: [], events: []} : {items: []}};
        });
        await box.invoke();
        if (["staleRoute", "logout", "newer"].includes(scenario)) assert.equal(box.logs.length, 0);
        else {
          const key = scenario === "failed" ? "failed" : action === "image-studio-refresh" ? "refreshed"
            : action === "image-studio-filter" ? "filtered" : action === "image-studio-filter-clear" ? "listed" : "paged";
          assert.deepEqual(box.logs, [{message: messages[locale][key], type: scenario === "failed" ? "error" : "success"}]);
        }
        all.push({kind, action, scenario});
      }
    assert.equal(all.length, 25);
  });
}

test("invalid restored filter keeps its error and fences the older in-flight read", async () => {
  let release;
  const pending = new Promise(resolve => {release = resolve;});
  const box = harness("list", "image-studio-refresh", "vi", async () => {await pending; return {data: {items: []}};});
  const old = box.invoke();
  assert.equal(box.imageStudioHydrationEpoch, 1);
  box.state.imageStudioReferences = {invalid: true};
  await box.invoke();
  assert.deepEqual(box.logs, [{message: "specific validation error", type: "error"}]);
  assert.equal(box.imageStudioHydrationEpoch, 2);
  release(); await old;
  assert.equal(box.logs.length, 1);
  assert.notEqual(box.state.imageStudioReadState, "ready");
});

for (const kind of ["list", "detail"]) {
  test(`${kind}: synchronous and asynchronous read errors respect route, session and request guards`, async () => {
    for (const scenario of ["syncThrow", "asyncReject", "routeChange", "logout", "newer"]) {
      const box = harness(kind, "image-studio-refresh", "vi", async () => {throw Error("unexpected API call");});
      const epochKey = kind === "detail" ? "imageStudioDetailHydrationEpoch" : "imageStudioHydrationEpoch";
      const otherKey = kind === "detail" ? "imageStudioHydrationEpoch" : "imageStudioDetailHydrationEpoch";
      const otherEpoch = box[otherKey];
      let reject;
      const deferred = new Promise((_, fail) => {reject = fail;});
      const reader = scenario === "syncThrow" ? () => {throw Error("specific validation error");}
        : scenario === "asyncReject" ? () => Promise.reject(Error("specific validation error")) : () => deferred;
      const pending = box.readWithFeedback(box.route, kind, reader, "refreshed", "Đã làm mới.");
      if (scenario === "routeChange") box.route = "/other";
      if (scenario === "logout") box.state.session = {authenticated: false};
      if (scenario === "newer") box[epochKey]++;
      if (!["syncThrow", "asyncReject"].includes(scenario)) reject(Error("specific validation error"));
      await pending;
      assert.deepEqual(box.logs, ["syncThrow", "asyncReject"].includes(scenario)
        ? [{message: "specific validation error", type: "error"}] : [], scenario);
      assert.equal(box[otherKey], otherEpoch, "other request kind remains unchanged");
    }
  });
}

test("direct invalid input and denied capability retain their validation", async () => {
  const api = async () => {throw Error("API must not be called");};
  const invalid = harness("list", "image-studio-filter", "vi", api); invalid.fields.q = "invalid";
  await assert.rejects(invalid.invoke(), /invalid filter/);
  const denied = harness("list", "image-studio-page", "vi", api); denied.state.capabilities["image-studio-page"] = false;
  await assert.rejects(denied.invoke(), /signed Web session/);
  assert.deepEqual(invalid.logs, []); assert.deepEqual(denied.logs, []);
});

test("historical snapshot removes only the five registered messages", () => {
  for (const locale of ["vi", "en", "zh"]) {
    const entries = [...Object.entries(messages[locale]).map(([key, value]) => ["imageStudioReadFeedback." + key, value]), [123, "CUSTOMER"]];
    const old = imageStudioReadFeedbackHistoricalSnapshot(entries, locale);
    assert.equal(old.length, 1); assert.equal(old[0], entries[5]);
    const mixed = entries.map(row => [...row]); mixed[0][1] = "UNREVIEWED";
    assert.throws(() => imageStudioReadFeedbackHistoricalSnapshot(mixed, locale));
  }
});
