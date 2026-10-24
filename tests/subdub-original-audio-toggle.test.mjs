import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
const source = readFileSync("static/portal/portal.js", "utf8");
const start = source.indexOf("  const SUBDUB_PRODUCT_MODES = Object.freeze({"), end = source.indexOf("\n  function renderDocumentHub", start);
const c = source.indexOf("  function subDubVoiceCompanionUrl("), ce = source.indexOf("\n  }", c);
assert.ok(start >= 0 && end > start && c >= 0 && ce > c, "actual renderer boundaries");
const renderer = source.slice(c, ce + 4) + "\n" + source.slice(start, end);
const escape = (v) => String(v ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
const modes = [["SUBTITLE_ONLY", "subtitle_only"], ["TRANSLATED_SUBTITLE", "translated_subtitle"], ["DUBBING_ONLY", "dubbing_only"], ["SUBTITLE_PLUS_DUBBING", "subtitle_plus_dubbing"]];
const session = { authenticated: true, csrfToken: "unit-account-a" };
const seed = (volume = "37") => ({ shared: { original_volume: volume, dubbing_volume: "0", dubbing_mute_ack: "true", target_language: "ja",
  target_language_custom: "pt-BR", voice_lane: "custom_voice", subtitle_position: "top_left", sub_display_type: "bilingual" },
  modes: { DUBBING_ONLY: {}, SUBTITLE_PLUS_DUBBING: { "subdub-combined-output-format": "vtt" } } });
function harness(saved = seed(), signed = true) {
  const drafts = new Map([["/foreign", { keep: "foreign" }]]), win = { location: { search: "?mode=dubbing_only" } };
  const api = new Function("window", "interfaceLocaleFor", "safeText", "badge", "renderHero", "transientFormDrafts", "clearTransientFormDraft",
    renderer + "\nreturn {render:renderSubDubHub,update:updateSubDubLocalVolume,sync:synchronizeSubDubWorkspaceDraftSession," +
    "snapshot:subDubDraftSnapshot,capture:captureSubDubDraft,apply:applySubDubDraftDom,normalize:normalizeSubDubDraftValue," +
    "summary:updateSubDubSettingsSummary,voice:updateSubDubVoiceLaneSelection};")(
    win, (context) => context.locale, escape, () => "", () => "", drafts, (route) => drafts.delete(route));
  if (signed) api.sync({ session }); drafts.set("/subdub", structuredClone(saved));
  return { api, drafts, win, render(query, locale = "en", ready = true) {
    win.location.search = "?mode=" + query; return api.render({ title: "SubDub" }, { locale, session: ready ? session : null, wallet: null });
  } };
}
const attr = (tag, key) => tag.match(new RegExp('(?:^|\\s)' + key + '="([^"]*)"'))?.[1] ?? null;
const inputs = (html) => Array.from(html.matchAll(/<input\b[^>]*>/g), (m) => m[0]);
const switches = (html) => inputs(html).filter((tag) => /\sdata-subdub-original-audio-toggle(?:\s|>)/.test(tag));
const bool = (tag, key) => new RegExp("(?:^|\\s)" + key + "(?=\\s|>)").test(tag);
const panelHtml = (html, mode) => html.match(new RegExp('<section\\b[^>]*data-subdub-mode-panel="' + mode + '"[^>]*>[\\s\\S]*?</section>'))?.[0] || "";
const review = (html, key) => { const m = html.match(new RegExp('<span[^>]*data-subdub-setting="' + key + '"[^>]*>([^<]*)</span>')); assert.ok(m, key); return m[1]; };
function fixture() {
  const root = { active: "DUBBING_ONLY", dataset: { subdubAuthoringReady: "true" } }, panels = [], rows = { innerHTML: "" };
  function control(panel, type, value, attributes = {}, tagName = "INPUT") {
    const item = { tagName, type, name: attributes.name || "", value, checked: false, disabled: false, readOnly: false,
      validity: { badInput: false }, attributes: { type, ...attributes }, options: [{ value: "ja" }, { value: "top_left" }, { value: "bilingual" }, { value: "vtt" }],
      getAttribute(key) { return this.attributes[key] ?? null; }, hasAttribute(key) { return Object.hasOwn(this.attributes, key); },
      setAttribute(key, value) { this.attributes[key] = String(value); }, closest(selector) {
        if (selector === ".portal-subdub-hub") return root;
        if (selector === "[data-subdub-mode-panel]" || selector === ".portal-subdub-hub [data-subdub-mode-panel]") return panel;
        if (selector === ".portal-subdub-voice-lanes" || selector === ".portal-subdub-hub [data-subdub-language-search]") return null;
        if (selector === ".portal-subdub-hub [data-subdub-local-volume]") return this.hasAttribute("data-subdub-local-volume") ? this : null;
        if (selector === ".portal-subdub-hub [data-subdub-local-volume], .portal-subdub-hub [data-subdub-original-audio-toggle]")
          return this.hasAttribute("data-subdub-local-volume") || this.hasAttribute("data-subdub-original-audio-toggle") ? this : null;
        if (selector === ".portal-subdub-hub [data-subdub-voice-lane-input]") return this.hasAttribute("data-subdub-voice-lane-input") ? this : null;
        if (selector === '.portal-subdub-hub [data-subdub-mode-panel] select[name="target_language"]') return this.tagName === "SELECT" && this.name === "target_language" ? this : null;
        throw Error("unexpected closest " + selector);
      } }; return item;
  }
  for (const mode of ["DUBBING_ONLY", "SUBTITLE_PLUS_DUBBING"]) {
    const p = { mode, hidden: mode !== root.active, getAttribute(key) { assert.equal(key, "data-subdub-mode-panel"); return this.mode; } };
    p.range = control(p, "range", "37", { "data-subdub-local-volume": "original" });
    p.number = control(p, "number", "37", { "data-subdub-local-volume": "original" });
    p.toggle = control(p, "checkbox", "", { "data-subdub-original-audio-toggle": "" }); p.toggle.checked = true;
    p.dubRange = control(p, "range", "0", { "data-subdub-local-volume": "dubbing" });
    p.dubNumber = control(p, "number", "0", { "data-subdub-local-volume": "dubbing" });
    p.ack = control(p, "checkbox", "", { name: "dubbing_mute_ack", "data-subdub-mute-ack": "" }); p.ack.checked = true;
    p.voice = control(p, "radio", "custom_voice", { "data-subdub-voice-lane-input": "" }); p.voice.checked = true;
    p.language = control(p, "select-one", "ja", { name: "target_language" }, "SELECT");
    p.iso = control(p, "text", "pt-BR", { name: "target_language_custom" });
    p.fields = [p.range, p.number, p.toggle, p.dubRange, p.dubNumber, p.ack, p.voice, p.language, p.iso];
    if (mode === "SUBTITLE_PLUS_DUBBING") for (const [name, value] of [["subdub_combo_subtitle_position", "top_left"], ["sub_display_type", "bilingual"], ["subdub-combined-output-format", "vtt"]])
      p.fields.push(control(p, "select-one", value, { name }, "SELECT"));
    p.output = { textContent: "37%" }; p.dubOutput = { textContent: "0%" }; p.error = { hidden: true }; p.dubError = { hidden: true };
    p.muted = { hidden: true }; p.dubMuted = { hidden: false };
    p.querySelector = (selector) => {
      const lookup = {
        'input[type="range"][data-subdub-local-volume="original"]': p.range, 'input[type="number"][data-subdub-local-volume="original"]': p.number,
        'input[type="checkbox"][data-subdub-original-audio-toggle]': p.toggle, '[data-subdub-original-audio-toggle]': p.toggle,
        'input[type="range"][data-subdub-local-volume="dubbing"]': p.dubRange, 'input[type="number"][data-subdub-local-volume="dubbing"]': p.dubNumber,
        '[data-subdub-volume-output="original"]': p.output, '[data-subdub-volume-output="dubbing"]': p.dubOutput,
        '[data-subdub-volume-error="original"]': p.error, '[data-subdub-volume-error="dubbing"]': p.dubError,
        '[data-subdub-volume-muted="original"]': p.muted, '[data-subdub-volume-muted="dubbing"]': p.dubMuted,
        "[data-subdub-mute-ack]": p.ack, "[data-subdub-voice-lane-input]:checked": p.voice.checked ? p.voice : null
      };
      if (Object.hasOwn(lookup, selector)) return lookup[selector]; throw Error("unexpected panel selector " + selector);
    };
    p.querySelectorAll = (selector) => { assert.equal(selector, "input, select, textarea"); return p.fields; }; panels.push(p);
  }
  const sourceState = control(null, "radio", "with_subtitles", { name: "subdub-subtitle-source-state" }); sourceState.checked = true;
  const stage1 = { querySelectorAll(selector) { assert.equal(selector, "input, select, textarea"); return [sourceState]; } };
  root.getAttribute = (key) => { assert.equal(key, "lang"); return "en"; };
  root.querySelector = (selector) => {
    if (selector === '[data-subdub-stage="1"]') return stage1;
    if (selector === "[data-subdub-settings-rows]") return rows;
    if (selector === '[data-subdub-mode-select][aria-selected="true"]') return { getAttribute(key) { assert.equal(key, "data-subdub-mode-select"); return root.active; } };
    const m = selector.match(/^\[data-subdub-mode-panel="(DUBBING_ONLY|SUBTITLE_PLUS_DUBBING)"\]$/);
    if (m) return panels.find((p) => p.mode === m[1]) || null; throw Error("unexpected root selector " + selector);
  };
  root.querySelectorAll = (selector) => { assert.equal(selector, "[data-subdub-mode-panel]"); return panels; };
  return { root, panels, rows, p: panels[0], activate(mode) { root.active = mode; panels.forEach((p) => { p.hidden = p.mode !== mode; }); } };
}
const commit = (h, f) => { h.api.capture(f.root); assert.equal(h.api.summary(f.root), true); };
function delegate(type, api, log) {
  const marker = '    document.addEventListener("' + type + '", (event) => {', a = source.indexOf(marker);
  const b = source.indexOf("        updateSubDubSettingsSummary(subDubForm);", a), end = source.indexOf("\n      }", b);
  assert.ok(a >= 0 && b > a && end > b, "actual " + type + " SubDub delegate boundaries");
  const chunk = source.slice(source.indexOf("\n", a) + 1, end + 8);
  const names = ["updateSubDubLocalVolume", "updateSubDubVoiceLaneSelection", "captureSubDubDraft", "updateSubDubSettingsSummary", "updateSubDubLanguageSearch"];
  const functions = [api.update, () => { throw Error("unexpected voice call"); }, api.capture, api.summary, () => { throw Error("unexpected search call"); }];
  functions[1] = api.voice;
  const run = new Function("event", ...names, chunk);
  return (target) => run({ target }, ...functions.map((fn, index) => (...args) => { log.push(names[index]); return fn(...args); }));
}

test("twelve actual views associate two native switches with localized labels, volume state and ready/pending guards", () => {
  const labels = { vi: "Giữ âm thanh gốc", en: "Keep original audio", zh: "保留原始音频" };
  for (const [mode, query] of modes) for (const locale of ["vi", "en", "zh"]) for (const volume of ["0", "37"]) for (const ready of [true, false]) {
    const h = harness(seed(volume)), html = h.render(query, locale, ready), tags = switches(html);
    assert.equal(tags.length, 2); assert.deepEqual(tags.map((tag) => attr(tag, "id")), ["subdub-original-audio-toggle-dub", "subdub-original-audio-toggle-combo"]);
    for (const tag of tags) {
      assert.equal(attr(tag, "type"), "checkbox"); assert.equal(attr(tag, "role"), "switch"); assert.equal(attr(tag, "name"), null);
      assert.equal(bool(tag, "checked"), volume === "37"); assert.equal(bool(tag, "disabled"), !ready);
      const label = html.match(new RegExp('<label[^>]*for="' + attr(tag, "id") + '"[^>]*>([\\s\\S]*?)</label>'));
      assert.ok(label && label[1].includes(tag)); assert.equal(label[1].replace(/<[^>]*>/g, "").trim(), labels[locale]);
    }
    if (mode === "SUBTITLE_ONLY" || mode === "TRANSLATED_SUBTITLE") assert.equal(switches(panelHtml(html, mode)).length, 0);
    for (const id of ["subdub-source-file", "subdub-source-lang"]) assert.ok(bool(html.match(new RegExp('<(?:input|select)[^>]*id="' + id + '"[^>]*>'))[0], "disabled"));
    assert.match(html, /<button[^>]*disabled[^>]*portal-subdub-cta|<button[^>]*portal-subdub-cta[^>]*disabled/);
  }
  const initial = seed(); delete initial.shared.original_volume;
  const defaults = harness(initial).render("dubbing_only"); assert.ok(switches(defaults).every((tag) => bool(tag, "checked")));
  assert.equal(review(defaults, "original_volume"), "100%");
});

test("checkbox updater mutes 37, remembers and restores it idempotently with output/review and valid default100", () => {
  const h = harness(), f = fixture(), p = f.p; p.toggle.checked = false;
  assert.equal(h.api.update(p.toggle), true); commit(h, f);
  assert.deepEqual([p.range.value, p.number.value, p.toggle.checked, p.output.textContent, review(f.rows.innerHTML, "original_volume")], ["0", "0", false, "0%", "0%"]);
  assert.equal(h.drafts.get("/subdub").shared.original_volume_restore, "37");
  assert.equal(h.api.update(p.toggle), true); p.toggle.checked = true; assert.equal(h.api.update(p.toggle), true); commit(h, f);
  assert.deepEqual([p.range.value, p.number.value, p.toggle.checked, p.output.textContent, review(f.rows.innerHTML, "original_volume")], ["37", "37", true, "37%", "37%"]);
  assert.equal(h.api.update(p.toggle), true); assert.equal(p.range.value, "37");
  for (const restore of [undefined, "0", "101", "bad"]) {
    const d = seed("0"); d.shared.original_volume_restore = restore; const x = harness(d), g = fixture();
    g.p.range.value = g.p.number.value = "0"; g.p.toggle.checked = true; assert.equal(x.api.update(g.p.toggle), true);
    assert.deepEqual([g.p.range.value, g.p.number.value, g.p.toggle.checked], ["100", "100", true]);
  }
});

test("manual zero and 1/100 boundaries synchronize original switch while invalid/badInput and dubbing0/200 stay isolated", () => {
  const h = harness(), f = fixture(), p = f.p; p.range.value = "0"; assert.equal(h.api.update(p.range), true);
  assert.equal(p.toggle.checked, false); assert.equal(h.drafts.get("/subdub").shared.original_volume_restore, "37");
  p.toggle.checked = true; assert.equal(h.api.update(p.toggle), true); assert.equal(p.range.value, "37");
  for (const value of ["1", "100"]) {
    p.number.value = value; assert.equal(h.api.update(p.number), true); assert.equal(p.range.value, value);
    assert.equal(p.toggle.checked, true); assert.equal(h.drafts.get("/subdub").shared.original_volume_restore, value);
  }
  for (const value of ["", "-1", "101", "1.5", "bad"]) {
    p.number.value = value; const before = JSON.stringify([...h.drafts]); assert.equal(h.api.update(p.number), false);
    assert.equal(p.range.value, "100"); assert.equal(p.toggle.checked, true); assert.equal(p.number.getAttribute("aria-invalid"), "true"); assert.equal(p.number.value, value); assert.equal(p.output.textContent, "100%");
    assert.equal(p.error.hidden, false); assert.equal(JSON.stringify([...h.drafts]), before);
  }
  p.number.value = "37"; p.number.validity.badInput = true; assert.equal(h.api.update(p.number), false); assert.equal(p.range.value, "100");
  p.number.validity.badInput = false; p.number.value = "100";
  for (const [volume, ack] of [["0", true], ["200", false]]) {
    p.dubNumber.value = volume; assert.equal(h.api.update(p.dubNumber), true); assert.equal(p.dubRange.value, volume);
    assert.equal(p.ack.checked, ack); assert.equal(p.range.value, "100"); assert.equal(p.toggle.checked, true);
  }
});

test("private metadata canonicalizes only positive 1..100 and actual capture/same-session/replacement/logout preserve fences", () => {
  const h = harness(), f = fixture();
  for (const [input, expected] of [[1, "1"], ["037", "37"], [100, "100"]]) assert.equal(h.api.normalize("original_volume_restore", input), expected);
  for (const bad of [0, "0", 101, "", " ", NaN, 1.5, true, false, null, undefined]) assert.equal(h.api.normalize("original_volume_restore", bad), null);
  assert.equal(h.api.normalize("original_volume", 0), "0"); assert.equal(h.api.normalize("dubbing_volume", 200), "200");
  const d = seed(); d.shared.original_volume_restore = "37"; h.drafts.set("/subdub", d); commit(h, f);
  assert.equal(h.api.snapshot().shared.original_volume_restore, "37"); assert.equal(h.api.snapshot().shared.voice_lane, "custom_voice");
  const before = JSON.stringify([...h.drafts]); h.api.sync({ session }); assert.equal(JSON.stringify([...h.drafts]), before);
  h.api.sync({ session: { authenticated: true, csrfToken: "unit-account-b" } }); assert.equal(h.drafts.has("/subdub"), false); assert.deepEqual(h.drafts.get("/foreign"), { keep: "foreign" });
  h.drafts.set("/subdub", d); h.api.sync({ session: null }); assert.equal(h.drafts.has("/subdub"), false); assert.deepEqual(h.drafts.get("/foreign"), { keep: "foreign" });
});

test("actual apply/root draft/mode reconstruction preserves muted restore37 and saved/custom metadata across both panels", () => {
  for (const voice of ["saved_voice", "custom_voice"]) {
    const d = seed("0"); d.shared.original_volume_restore = "37"; d.shared.voice_lane = voice; const h = harness(d), f = fixture();
    for (const [mode, query] of [["DUBBING_ONLY", "dubbing_only"], ["SUBTITLE_PLUS_DUBBING", "subtitle_plus_dubbing"], ["DUBBING_ONLY", "dubbing_only"]]) {
      f.activate(mode); const p = f.panels.find((p) => p.mode === mode); p.voice.value = voice;
      h.api.apply(f.root, h.api.snapshot(), mode); assert.equal(p.toggle.checked, false); assert.equal(p.range.value, "0"); assert.equal(p.dubRange.value, "0"); assert.equal(p.ack.checked, true);
      commit(h, f); assert.equal(h.api.snapshot().shared.original_volume_restore, "37"); assert.equal(bool(switches(panelHtml(h.render(query), mode))[0], "checked"), false);
    }
    f.p.toggle.checked = true; assert.equal(h.api.update(f.p.toggle), true); commit(h, f);
    const shared = h.api.snapshot().shared; assert.equal(shared.original_volume, "37"); assert.equal(shared.voice_lane, voice); assert.equal(shared.target_language, "ja");
    assert.equal(shared.target_language_custom, "pt-BR"); assert.equal(shared.subtitle_position, "top_left"); assert.equal(shared.dubbing_mute_ack, "true");
    assert.equal(h.api.snapshot().modes.SUBTITLE_PLUS_DUBBING["subdub-combined-output-format"], "vtt"); assert.deepEqual(h.drafts.get("/foreign"), { keep: "foreign" });
  }
});

test("both real delegated chunks update before capture/review and reject toggle identity/type/readiness/invalid-range writes", () => {
  const h = harness(), f = fixture(), p = f.p, log = [];
  for (const type of ["input", "change"]) {
    const run = delegate(type, h.api, log); log.length = 0; p.toggle.checked = false; run(p.toggle);
    assert.deepEqual(log, type === "input" ? ["updateSubDubLocalVolume", "captureSubDubDraft", "updateSubDubSettingsSummary"] :
      ["updateSubDubLocalVolume", "updateSubDubVoiceLaneSelection", "captureSubDubDraft", "updateSubDubSettingsSummary"]);
    assert.equal(p.range.value, "0"); assert.equal(review(f.rows.innerHTML, "original_volume"), "0%"); assert.equal(h.api.snapshot().shared.original_volume_restore, "37");
    p.toggle.checked = true; run(p.toggle); assert.equal(p.range.value, "37"); assert.equal(review(f.rows.innerHTML, "original_volume"), "37%"); assert.equal(p.dubRange.value, "0"); assert.equal(p.ack.checked, true);
  }
  const changes = [(g) => { g.p.toggle.disabled = true; }, (g) => { g.p.toggle.readOnly = true; }, (g) => { g.root.dataset.subdubAuthoringReady = "false"; },
    (g) => { g.p.hidden = true; }, (g) => { g.p.mode = "SUBTITLE_ONLY"; }, (g) => { g.p.toggle.type = "text"; }, (g) => { g.p.number.disabled = true; },
    (g) => { g.p.range.readOnly = true; }, (g) => { g.p.range.value = "invalid"; }, (g) => { g.p.range.validity.badInput = true; },
    (g) => { g.p.number.type = "range"; }, (g) => { g.p.range.type = "number"; },
    (g) => { const query = g.p.querySelector; g.p.querySelector = (s) => s === 'input[type="number"][data-subdub-local-volume="original"]' ? null : query(s); },
    (g) => { const closest = g.p.toggle.closest; g.p.toggle.closest = function (s) { return s === "[data-subdub-mode-panel]" ? null : closest.call(this, s); }; },
    (g) => { g.root.dataset = {}; }, (g) => { g.p.querySelector = null; }];
  for (const change of changes) { const x = harness(), g = fixture(); change(g); const before = JSON.stringify([g.p.range.value, g.p.number.value, g.p.toggle.checked, [...x.drafts]]);
    assert.equal(x.api.update(g.p.toggle), false); assert.equal(JSON.stringify([g.p.range.value, g.p.number.value, g.p.toggle.checked, [...x.drafts]]), before);
    if (typeof g.p.querySelector === "function") for (const type of ["input", "change"]) {
      delegate(type, x.api, [])(g.p.toggle); assert.equal(x.api.snapshot().shared.original_volume_restore, undefined);
      assert.deepEqual(x.drafts.get("/foreign"), { keep: "foreign" });
    }
  }
  const clone = { ...p.toggle }; const before = JSON.stringify([...h.drafts]); assert.equal(h.api.update(clone), false); assert.equal(JSON.stringify([...h.drafts]), before);
  const unsigned = harness(seed(), false), g = fixture(); assert.equal(unsigned.api.update(g.p.toggle), false); assert.equal(unsigned.drafts.get("/subdub").shared.original_volume_restore, undefined);
});
