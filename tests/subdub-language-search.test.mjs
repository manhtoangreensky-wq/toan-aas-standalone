import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const portalPath = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../static/portal/portal.js");
const portalSource = fs.readFileSync(portalPath, "utf8");
const normStart = portalSource.indexOf("function normalizeCatalogSearch");
const normEnd = portalSource.indexOf("\n  }", normStart) + 4;
const normCode = portalSource.slice(normStart, normEnd);
const blockStart = portalSource.indexOf("  const SUBDUB_PRODUCT_MODES = Object.freeze({");
const blockEnd = portalSource.indexOf("\n  function renderDocumentHub", blockStart);
const blockCode = portalSource.slice(blockStart, blockEnd);
const ioSpy = () => { throw new Error("I/O disallowed"); };
const blockedStorage = { getItem: ioSpy, setItem: ioSpy, removeItem: ioSpy };
const draftsMap = new Map([["__sentinel", "safe"]]);
const extractFn = new Function(
  "transientFormDrafts", "safeText", "fetch", "XMLHttpRequest",
  "localStorage", "sessionStorage", "setTimeout", "setInterval",
  normCode + "\n" + blockCode + "\nreturn typeof updateSubDubLanguageSearch === 'function' ? updateSubDubLanguageSearch : null;"
);
const updateSubDubLanguageSearch = extractFn(
  draftsMap, (v) => String(v ?? ""), ioSpy, ioSpy, blockedStorage, blockedStorage, ioSpy, ioSpy
);
function createFixture({ locale = "vi", selected = "vi", query = "", mode = "translate" } = {}) {
  const selectId = mode === "dub" ? "subdub-target-lang-dub" : (mode === "combo" ? "subdub-shared-target-lang" : "subdub-target-lang");
  const searchId = selectId + "-search", statusId = selectId + "-search-status";
  let selectValue = selected, options = [];
  const select = {
    id: selectId, name: "target_language",
    get value() { return selectValue; }, set value(v) { selectValue = v; },
    replaceChildren(...newOpts) {
      options = newOpts;
      const found = newOpts.find((o) => o.value === selectValue || o.selected);
      selectValue = found ? found.value : (newOpts[0]?.value || "");
    },
    get options() { return options; },
    dispatchEvent() { throw new Error("no dispatch"); }, focus() { throw new Error("no focus"); }
  };
  const status = {
    id: statusId, textContent: "",
    set innerHTML(_) { throw new Error("no innerHTML"); }, get innerHTML() { throw new Error("no innerHTML"); }
  };
  const doc = { createElement: (tag) => (tag === "option" ? {
    tag: "option", value: "", textContent: "", selected: false,
    set innerHTML(_) { throw new Error("no innerHTML"); }
  } : {}) };
  const inputAttrs = new Map([
    ["type", "search"], ["data-subdub-language-search", ""],
    ["data-subdub-language-locale", locale], ["aria-controls", selectId], ["aria-describedby", statusId]
  ]);
  const panel = {
    getAttribute: (n) => (n === "data-subdub-mode-panel" ? mode : null),
    setAttribute() {},
    querySelector(sel) {
      if (sel === 'select[name="target_language"]') return select;
      if (sel === "[data-subdub-language-search-status]") return status;
      if (sel === "[data-subdub-language-search]") return input;
      return null;
    }
  };
  const input = {
    id: searchId, type: "search", value: query, ownerDocument: doc,
    hasAttribute: (a) => inputAttrs.has(a), getAttribute: (a) => inputAttrs.get(a) ?? null,
    setAttribute: (a, v) => inputAttrs.set(a, v), removeAttribute: (a) => inputAttrs.delete(a),
    closest(sel) {
      if (sel.includes("data-subdub-language-search")) return input;
      if (sel.includes("data-subdub-mode-panel") || sel.includes("portal-subdub-hub")) return panel;
      return null;
    },
    dispatchEvent() { throw new Error("no dispatch"); }, focus() { throw new Error("no focus"); }
  };
  return { panel, select, status, input, doc };
}
test("B402: helper search query, pin selected, literal count/IDs across VI/EN/ZH", () => {
  assert.ok(updateSubDubLanguageSearch, "updateSubDubLanguageSearch must be defined");
  for (const [q, expected, count] of [
    ["tieng nhat", ["vi", "ja"], 1],
    ["Japanese", ["vi", "ja"], 1],
    ["日语", ["vi", "ja"], 1],
    ["zh", ["vi", "zh", "zh_cn", "zh_tw"], 3],
    ["duc", ["vi", "de"], 1]
  ]) {
    const f = createFixture({ locale: "vi", selected: "vi", query: q });
    assert.equal(updateSubDubLanguageSearch(f.input), true);
    assert.deepEqual(f.select.options.map((o) => o.value), expected);
    assert.equal(f.select.value, "vi");
    assert.match(f.status.textContent, new RegExp(`^${count} `));
  }
  const fDe = createFixture({ locale: "vi", selected: "de", query: "ja" });
  assert.equal(updateSubDubLanguageSearch(fDe.input), true);
  assert.deepEqual(fDe.select.options.map((o) => o.value), ["ja", "de"]);
  assert.equal(fDe.select.value, "de");
  const fEn = createFixture({ locale: "en", selected: "vi", query: "ja" });
  updateSubDubLanguageSearch(fEn.input);
  assert.equal(fEn.select.options.find((o) => o.value === "ja")?.textContent, "Japanese");
  assert.match(fEn.status.textContent, /1 matching languages/);
  const fZh = createFixture({ locale: "zh", selected: "vi", query: "ja" });
  updateSubDubLanguageSearch(fZh.input);
  assert.equal(fZh.select.options.find((o) => o.value === "ja")?.textContent, "日语");
  assert.match(fZh.status.textContent, /找到 1 种语言/);
  const fEmpty = createFixture({ locale: "vi", selected: "vi", query: "" });
  updateSubDubLanguageSearch(fEmpty.input);
  assert.equal(fEmpty.select.options.length, 21);
  assert.match(fEmpty.status.textContent, /^21 /);
  const fNoMatch = createFixture({ locale: "vi", selected: "vi", query: "notfoundxyz" });
  updateSubDubLanguageSearch(fNoMatch.input);
  assert.deepEqual(fNoMatch.select.options.map((o) => o.value), ["vi"]);
  assert.equal(fNoMatch.select.value, "vi");
  assert.match(fNoMatch.status.textContent, /Không tìm thấy/);

  fNoMatch.input.value = "";
  updateSubDubLanguageSearch(fNoMatch.input);
  assert.equal(fNoMatch.select.options.length, 21);
});

test("B402: 64 char boundary, HTML safety, zero IO/timer/draft mutation", () => {
  assert.ok(updateSubDubLanguageSearch, "updateSubDubLanguageSearch must be defined");
  const f64 = createFixture({ selected: "vi", query: "ja" + " ".repeat(62) + "zz" });
  assert.equal(updateSubDubLanguageSearch(f64.input), true);
  assert.deepEqual(f64.select.options.map((o) => o.value), ["vi", "ja"]);
  assert.equal(f64.input.value, "ja" + " ".repeat(62) + "zz");

  const fHtml = createFixture({ selected: "vi", query: "<img src=x onerror=alert(1)>" });
  assert.equal(updateSubDubLanguageSearch(fHtml.input), true);
  assert.deepEqual(fHtml.select.options.map((o) => o.value), ["vi"]);
  assert.match(fHtml.status.textContent, /Không tìm thấy/);
  assert.equal(draftsMap.size, 1);
  assert.equal(draftsMap.get("__sentinel"), "safe");
});

test("B402: invalid input, partial DOM, malformed IDs -> false + strict no-change", () => {
  assert.ok(updateSubDubLanguageSearch, "updateSubDubLanguageSearch must be defined");
  assert.equal(updateSubDubLanguageSearch(null), false);
  assert.equal(updateSubDubLanguageSearch({}), false);

  const negatives = [
    (f) => f.input.removeAttribute("data-subdub-language-search"),
    (f) => f.input.setAttribute("type", "text"),
    (f) => f.input.setAttribute("disabled", "true"),
    (f) => { f.input.closest = () => null; },
    (f) => { f.input.ownerDocument = null; },
    (f) => f.input.setAttribute("aria-controls", "["),
    (f) => f.input.setAttribute("aria-describedby", "["),
    (f) => { f.select.value = "unknown_lang"; },
    (f) => { f.select.replaceChildren = null; },
    (f) => { f.panel.querySelector = null; }
  ];
  for (const mutate of negatives) {
    const f = createFixture({ query: "ja" });
    assert.equal(updateSubDubLanguageSearch(f.input), true);
    mutate(f);
    const before = [f.select.options, f.select.value, f.status.textContent];
    assert.equal(updateSubDubLanguageSearch(f.input), false);
    assert.strictEqual(f.select.options, before[0]);
    assert.equal(f.select.value, before[1]);
    assert.equal(f.status.textContent, before[2]);
  }
});

test("B402: delegated order contract and search change skip", () => {
  const inputStart = portalSource.indexOf('document.addEventListener("input"');
  const keydownStart = portalSource.indexOf('document.addEventListener("keydown"', inputStart);
  assert.ok(inputStart > 0 && keydownStart > inputStart, "bindInteractions chunk present");
  const chunk = portalSource.slice(inputStart, keydownStart);
  const listeners = {}, calls = [];
  const fakeDoc = { addEventListener: (t, cb) => { listeners[t] = cb; } };
  const runDelegated = new Function(
    "document", "updateSubDubLocalVolume", "updateSubDubVoiceLaneSelection",
    "captureSubDubDraft", "updateSubDubSettingsSummary", "updateSubDubLanguageSearch",
    chunk
  );
  runDelegated(fakeDoc, () => calls.push("volume"), () => calls.push("voice"), () => calls.push("capture"), () => calls.push("summary"), () => calls.push("searchrefresh"));

  const f = createFixture();
  f.select.closest = (sel) => (sel.includes("target_language") ? f.select : (sel.includes("data-subdub-mode-panel") || sel.includes("portal-subdub-hub") ? f.panel : null));
  const makeEvt = (target) => ({ target });

  calls.length = 0; listeners.change(makeEvt(f.select));
  assert.deepEqual(calls, ["volume", "voice", "capture", "summary", "searchrefresh"]);

  calls.length = 0; listeners.input(makeEvt(f.input));
  assert.deepEqual(calls, ["searchrefresh"]);

  calls.length = 0; listeners.change(makeEvt(f.input));
  assert.deepEqual(calls, []);

  calls.length = 0;
  listeners.input(makeEvt({ closest: () => null }));
  listeners.change(makeEvt({ closest: () => null }));
  assert.deepEqual(calls, ["volume", "volume", "voice"]);
});

test("B402: mode reset clears search and restores 21 options before apply draft", () => {
  const modeStart = portalSource.indexOf("function updateSubDubModeSelection(");
  assert.ok(modeStart > 0, "updateSubDubModeSelection found");
  const returnTrueIdx = portalSource.indexOf("return true;", modeStart);
  const modeChunk = portalSource.slice(modeStart, portalSource.indexOf("\n  }", returnTrueIdx) + 4);

  assert.ok(updateSubDubLanguageSearch, "updateSubDubLanguageSearch must be defined");
  const events = [], fixtures = [
    createFixture({ mode: "translate", selected: "vi", query: "ja" }),
    createFixture({ mode: "dub", selected: "en", query: "ja" }),
    createFixture({ mode: "combo", selected: "de", query: "ja" })
  ];
  fixtures.forEach((f) => {
    assert.equal(updateSubDubLanguageSearch(f.input), true);
    assert.ok(f.select.options.length < 21);
  });
  const hub = {
    querySelectorAll(sel) {
      if (sel === "[data-subdub-language-search]") return fixtures.map((f) => f.input);
      if (sel === "[data-subdub-mode-panel]") return fixtures.map((f) => f.panel);
      return [];
    },
    querySelector: () => null
  };
  const modeBtn = {
    closest: (s) => (s === ".portal-subdub-hub" ? hub : null),
    getAttribute: (n) => (n === "data-subdub-mode-select" ? "dub" : (n === "data-subdub-mode-query" ? "dubbing" : ""))
  };
  const runMode = new Function(
    "captureSubDubDraft", "applySubDubDraftDom", "subDubDraftSnapshot",
    "updateSubDubSettingsSummary", "updateSubDubLanguageSearch",
    modeChunk + "\nreturn updateSubDubModeSelection;"
  );
  const modeFn = runMode(
    () => events.push("capture"), () => {
      events.push("apply");
      assert.deepEqual(fixtures.map((f) => f.input.value), ["", "", ""]);
      assert.deepEqual(fixtures.map((f) => f.select.options.length), [21, 21, 21]);
      assert.deepEqual(fixtures.map((f) => f.select.value), ["vi", "en", "de"]);
    },
    () => ({}), () => events.push("summary"),
    updateSubDubLanguageSearch
  );
  const res = modeFn(modeBtn, { location: { href: "http://localhost" }, history: { replaceState() {} } });
  assert.equal(res, true);
  assert.deepEqual(events, ["capture", "apply", "summary"]);
});
