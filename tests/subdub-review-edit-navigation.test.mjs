import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const start = source.indexOf("  const SUBDUB_PRODUCT_MODES = Object.freeze({"), end = source.indexOf("\n  function renderDocumentHub", start);
const companion = source.indexOf("  function subDubVoiceCompanionUrl(");
assert.ok(start >= 0 && end > start && companion >= 0, "actual renderer boundaries");
const renderer = source.slice(companion, source.indexOf("\n  }", companion) + 4) + "\n" + source.slice(start, end);
const escape = (v) => String(v ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
const decode = (v) => v.replaceAll("&quot;", '"').replaceAll("&#39;", "'").replaceAll("&lt;", "<").replaceAll("&gt;", ">").replaceAll("&amp;", "&");
const modes = [["SUBTITLE_ONLY", "subtitle_only"], ["TRANSLATED_SUBTITLE", "translated_subtitle"], ["DUBBING_ONLY", "dubbing_only"], ["SUBTITLE_PLUS_DUBBING", "subtitle_plus_dubbing"]];
const keys = {
  SUBTITLE_ONLY: ["source_subtitle_state", "subtitle_position", "output_format", "subtitle_format"],
  TRANSLATED_SUBTITLE: ["source_subtitle_state", "target_language", "subtitle_position", "output_format", "sub_display_type"],
  DUBBING_ONLY: ["source_subtitle_state", "target_language", "voice_lane", "original_volume", "dubbing_volume"],
  SUBTITLE_PLUS_DUBBING: ["source_subtitle_state", "target_language", "voice_lane", "original_volume", "dubbing_volume", "subtitle_position", "output_format", "sub_display_type"]
};
const seed = () => ({ shared: { source_subtitle_state: "with_subtitles", target_language: "ja", target_language_custom: "pt-BR", voice_lane: "custom_voice",
  original_volume: "0", dubbing_volume: "200", subtitle_position: "top_left", sub_display_type: "bilingual" },
  modes: { SUBTITLE_ONLY: { "subdub-source-output-format": "vtt", subtitle_format: "short" }, TRANSLATED_SUBTITLE: { "subdub-translated-output-format": "vtt" }, DUBBING_ONLY: {}, SUBTITLE_PLUS_DUBBING: { "subdub-combined-output-format": "vtt" } } });
function create(mode, locale = "en", draft = seed()) {
  const query = modes.find(([key]) => key === mode)[1], drafts = new Map([["/subdub", structuredClone(draft)]]);
  const win = { location: { search: "?mode=" + query, href: "https://app.example/subdub?mode=" + query },
    history: { replaceState() { throw Error("unexpected history write"); } }, dispatchEvent() { throw Error("unexpected dispatch"); } };
  const api = new Function("window", "interfaceLocaleFor", "safeText", "badge", "renderHero", "transientFormDrafts",
    renderer + '\nreturn { render: renderSubDubHub, copy: SUBDUB_PRESENTATION_COPY, snapshot: subDubDraftSnapshot, update: updateSubDubSettingsSummary, focus: typeof focusSubDubReviewSetting === "function" ? focusSubDubReviewSetting : null };')(
    win, (context) => context.locale, escape, () => "", () => "", drafts);
  return { api, drafts, win, render: () => api.render({ title: "SubDub" }, { locale, wallet: null }) };
}
const attr = (tag, name) => { const m = tag.match(new RegExp('(?:^|\\s)' + name + '="([^"]*)"')); return m ? decode(m[1]) : null; };
const actions = (html) => Array.from(html.matchAll(/<button\b[^>]*data-subdub-review-edit="[^"]*"[^>]*>[\s\S]*?<\/button>/g), (m) => m[0]);
const actionKeys = (html) => actions(html).map((tag) => attr(tag, "data-subdub-review-edit"));
const rows = (html) => html.match(/<div class="portal-summary-item(?: portal-subdub-review-edit-row)?"[^>]*>[\s\S]*?<\/div>/g) || [];
const value = (html, key) => { const found = Array.from(html.matchAll(/<span\b[^>]*data-subdub-setting="([^"]+)"[^>]*>([^<]*)<\/span>/g)).filter((m) => m[1] === key);
  assert.equal(found.length, 1, "one exact review span " + key); return decode(found[0][2]); };
function fixture(mode) {
  const log = [], targets = {}, unchecked = [];
  function control(tagName, type, name, val, checked = false) {
    return { tagName, type, name, value: val, checked, disabled: false, inheritedDisabled: false, attributeDisabled: false,
      getAttribute(name) { return name === "disabled" && this.attributeDisabled ? "" : name === "data-subdub-mode-select" ? this.mode ?? null : null; },
      matches(selector) { assert.equal(selector, ":disabled"); return this.inheritedDisabled; },
      focus(...args) { assert.deepEqual(args, [], "native focus receives no options"); log.push(this); } };
  }
  targets.source_subtitle_state = control("INPUT", "radio", "subdub-subtitle-source-state", "with_subtitles", true);
  unchecked.push(control("INPUT", "radio", "subdub-subtitle-source-state", "without_subtitles", false));
  const descriptors = {
    target_language: ["SELECT", "select-one", "target_language", "ja"], target_language_custom: ["INPUT", "text", "target_language_custom", "pt-BR"],
    voice_lane: ["INPUT", "radio", "subdub_voice_lane_" + (mode === "DUBBING_ONLY" ? "dub" : "combo"), "custom_voice", true],
    original_volume: ["INPUT", "number", "", "0"], dubbing_volume: ["INPUT", "number", "", "200"],
    subtitle_position: ["SELECT", "select-one", "subdub_" + ({ SUBTITLE_ONLY: "source", TRANSLATED_SUBTITLE: "translated", SUBTITLE_PLUS_DUBBING: "combo" }[mode]) + "_subtitle_position", "top_left"],
    output_format: ["INPUT", "radio", ({ SUBTITLE_ONLY: "subdub-source-output-format", TRANSLATED_SUBTITLE: "subdub-translated-output-format", SUBTITLE_PLUS_DUBBING: "subdub-combined-output-format" }[mode]), "vtt", true],
    subtitle_format: ["SELECT", "select-one", "subtitle_format", "short"],
    sub_display_type: mode === "TRANSLATED_SUBTITLE" ? ["INPUT", "radio", "sub_display_type", "bilingual", true] : ["SELECT", "select-one", "sub_display_type", "bilingual"]
  };
  for (const key of keys[mode].filter((key) => key !== "source_subtitle_state")) targets[key] = control(...descriptors[key]);
  if (mode !== "SUBTITLE_ONLY") targets.target_language_custom = control(...descriptors.target_language_custom);
  for (const key of ["voice_lane", "output_format", "sub_display_type"]) if (targets[key]?.type === "radio")
    unchecked.push(control("INPUT", "radio", targets[key].name, key === "voice_lane" ? "saved_voice" : key === "output_format" ? "srt" : "single", false));
  const ranges = targets.original_volume ? [control("INPUT", "range", "", "0"), control("INPUT", "range", "", "200")] : [];
  const modeButton = control("BUTTON", "button", "", ""); modeButton.mode = mode;
  const sentinel = control("INPUT", "radio", "hidden-sibling", "do-not-focus", true);
  const panel = { hidden: false, ariaHidden: "false", getAttribute(name) { assert.equal(name, "aria-hidden"); return this.ariaHidden; },
    querySelector(selector) {
      switch (selector) {
        case 'select[name="target_language"]': return targets.target_language || null;
        case 'input[name="target_language_custom"]': return targets.target_language_custom || null;
        case '[data-subdub-voice-lane-input]:checked': return targets.voice_lane || null;
        case 'input[type="number"][data-subdub-local-volume="original"]': return targets.original_volume || null;
        case 'input[type="number"][data-subdub-local-volume="dubbing"]': return targets.dubbing_volume || null;
        case 'select[name^="subdub_"][name$="_subtitle_position"]': return targets.subtitle_position || null;
        case 'input[name$="-output-format"]:checked': return targets.output_format || null;
        case 'select[name="subtitle_format"]': return targets.subtitle_format || null;
        case 'select[name="sub_display_type"],input[name="sub_display_type"]:checked': return targets.sub_display_type || null;
        default: throw Error("unexpected active-panel selector: " + selector);
      }
    } };
  const root = { selected: modeButton, panel, state: { mode, search: "jap", url: "/subdub?mode=" + modes.find(([key]) => key === mode)[1] }, innerHTML: "preserved",
    querySelector(selector) {
      if (selector === '[data-subdub-mode-select][aria-selected="true"]') return this.selected;
      if (selector === '[data-subdub-stage="1"] input[name="subdub-subtitle-source-state"]:checked') return targets.source_subtitle_state || null;
      const match = selector.match(/^\[data-subdub-mode-panel="(SUBTITLE_ONLY|TRANSLATED_SUBTITLE|DUBBING_ONLY|SUBTITLE_PLUS_DUBBING)"\]$/);
      if (match) return match[1] === mode ? this.panel : { hidden: true, getAttribute: () => "true", querySelector: () => sentinel };
      throw Error("unexpected root selector: " + selector);
    } };
  const edit = (key) => ({ closest(selector) { assert.equal(selector, ".portal-subdub-hub"); return root; },
    getAttribute(name) { assert.equal(name, "data-subdub-review-edit"); return key; } });
  const snapshot = () => JSON.stringify({ state: root.state, html: root.innerHTML, controls: [...Object.values(targets), ...unchecked, ...ranges]
    .map(({ tagName, type, name, value, checked }) => ({ tagName, type, name, value, checked })) });
  return { root, panel, targets, modeButton, sentinel, unchecked, ranges, log, edit, snapshot };
}

test("localized Edit actions have the exact existing mode-dependent keysets in all twelve mode/locale views", () => {
  for (const locale of ["vi", "en", "zh"]) for (const [mode] of modes) {
    const html = create(mode, locale, { shared: {}, modes: {} }).render();
    assert.deepEqual(actionKeys(html), [...keys[mode], "mode"], locale + "/" + mode);
    for (const button of actions(html)) {
      assert.equal(attr(button, "type"), "button"); assert.equal(attr(button, "class"), "portal-subdub-review-edit");
      const action = { vi: "Sửa", en: "Edit", zh: "修改" }[locale];
      assert.ok(button.endsWith(">" + action + "</button>"));
      assert.ok(attr(button, "aria-label").startsWith(action + ": "));
    }
  }
});

test("readonly rows stay actionless, mode stays editable and custom ISO gets an action only when actually rendered", () => {
  for (const [mode] of modes) for (const custom of ["", "pt-BR"]) {
    const draft = seed(); draft.shared.target_language_custom = custom;
    const html = create(mode, "en", draft).render();
    assert.equal(actionKeys(html).filter((key) => key === "mode").length, 1);
    assert.equal(actionKeys(html).filter((key) => key === "target_language_custom").length, custom && mode !== "SUBTITLE_ONLY" ? 1 : 0);
    for (const key of ["source_file", "source_language"]) {
      const row = rows(html).filter((row) => row.includes('data-subdub-setting="' + key + '"'));
      assert.equal(row.length, 1); assert.equal(actions(row[0]).length, 0); assert.equal(attr(row[0], "class"), "portal-summary-item");
    }
    assert.equal(new Set(actionKeys(html)).size, actionKeys(html).length);
    assert.deepEqual(actionKeys(html).filter((key) => key !== "target_language_custom"), [...keys[mode], "mode"]);
  }
});

test("actual helper focuses each active typed field, stage-one radio or selected mode without touching hidden siblings", () => {
  for (const [mode] of modes) {
    const { api } = create(mode); assert.equal(typeof api.focus, "function", "real Edit focus helper exists");
    const f = fixture(mode);
    for (const key of [...keys[mode], ...(mode === "SUBTITLE_ONLY" ? [] : ["target_language_custom"]), "mode"]) {
      f.log.length = 0; assert.equal(api.focus(f.edit(key)), true, mode + "/" + key);
      assert.deepEqual(f.log, [key === "mode" ? f.modeButton : f.targets[key]]);
      assert.equal(f.log.includes(f.sentinel), false);
    }
    if (mode === "DUBBING_ONLY") for (const key of ["subtitle_position", "output_format", "subtitle_format", "sub_display_type"]) {
      f.log.length = 0; assert.equal(api.focus(f.edit(key)), false); assert.equal(f.log.length, 0);
    }
  }
});

test("invalid roots, keys, modes, panels and unavailable or disabled focus targets fail closed", () => {
  const { api } = create("DUBBING_ONLY"); assert.equal(typeof api.focus, "function");
  const cases = [
    ["null", () => null], ["no closest", () => ({})], ["outside", () => ({ closest: () => null })],
    ["bad key", (f) => f.edit("bad")], ["prototype key", (f) => f.edit("__proto__")], ["inherited key", (f) => f.edit("constructor")],
    ["missing mode", (f) => { f.root.selected = null; }], ["invalid mode", (f) => { f.modeButton.mode = "NO_MODE"; }],
    ["prototype mode", (f) => { f.modeButton.mode = "constructor"; }], ["missing mode key", (f) => { f.modeButton.mode = null; }],
    ["missing panel", (f) => { f.root.panel = null; }], ["hidden panel", (f) => { f.panel.hidden = true; }],
    ["aria-hidden panel", (f) => { f.panel.ariaHidden = "true"; }], ["missing target", (f) => { delete f.targets.target_language; }],
    ["own disabled", (f) => { f.targets.target_language.disabled = true; }], ["disabled attribute", (f) => { f.targets.target_language.attributeDisabled = true; }],
    ["inherited disabled", (f) => { f.targets.target_language.inheritedDisabled = true; }], ["missing focus", (f) => { f.targets.target_language.focus = null; }]
  ];
  for (const [name, setup] of cases) {
    const f = fixture("DUBBING_ONLY"), alternate = setup(f), button = alternate === undefined ? f.edit("target_language") : alternate, before = f.snapshot();
    assert.equal(api.focus(button), false, name); assert.equal(f.log.length, 0, name); assert.equal(f.snapshot(), before, name);
  }
});

test("real Edit invocation preserves checked radios, zero/two-hundred controls, draft, root state, URL and review", () => {
  for (const [mode] of modes) {
    const env = create(mode), f = fixture(mode); assert.equal(typeof env.api.focus, "function");
    const before = { controls: f.snapshot(), draft: JSON.stringify([...env.drafts]), normalized: JSON.stringify(env.api.snapshot()), window: JSON.stringify(env.win), html: env.render(), root: f.root };
    for (const key of [...keys[mode], "mode"]) assert.equal(env.api.focus(f.edit(key)), true, key);
    assert.equal(f.snapshot(), before.controls); assert.equal(JSON.stringify([...env.drafts]), before.draft);
    assert.equal(JSON.stringify(env.api.snapshot()), before.normalized); assert.equal(JSON.stringify(env.win), before.window);
    assert.equal(env.render(), before.html); assert.equal(f.root, before.root);
    if (f.targets.voice_lane) {
      assert.equal(f.targets.voice_lane.checked, true); assert.ok(f.unchecked.every((control) => control.checked === false));
      assert.equal(f.targets.original_volume.value, "0"); assert.equal(f.targets.dubbing_volume.value, "200");
      assert.deepEqual(f.ranges.map((control) => control.value), ["0", "200"]);
    }
  }
});

test("fresh nested locale copy is escaped while normal full voice, Japanese, ISO and mix review values remain exact", () => {
  const hostile = create("DUBBING_ONLY");
  hostile.api.copy.en.summaryEditAction = 'E<"&'; hostile.api.copy.en.targetLangDubLabel = 'L<"&';
  const button = actions(hostile.render()).find((tag) => attr(tag, "data-subdub-review-edit") === "target_language");
  assert.ok(button, "actual target-language Edit button exists");
  assert.ok(button.includes('aria-label="E&lt;&quot;&amp;: L&lt;&quot;&amp;"')); assert.ok(button.endsWith(">E&lt;&quot;&amp;</button>"));
  assert.ok(!hostile.render().includes('L<"&'));
  for (const mode of ["DUBBING_ONLY", "SUBTITLE_PLUS_DUBBING"]) {
    const normal = create(mode), html = normal.render();
    assert.equal(value(html, "voice_lane"), "Uploaded voice with consent"); assert.equal(value(html, "target_language"), "Japanese");
    assert.equal(value(html, "target_language_custom"), "pt-BR"); assert.equal(value(html, "original_volume"), "0%"); assert.equal(value(html, "dubbing_volume"), "200%");
    assert.equal(normal.api.copy.en.summaryEditAction, "Edit", "fresh renderer instance does not retain hostile copy");
  }
});

test("identical input/change summaries retain their child nodes while changed draft or mode rerenders once", () => {
  const env = create("TRANSLATED_SUBTITLE"), writes = [];
  let html = "", child = null;
  const region = { get innerHTML() { return html; }, set innerHTML(next) { writes.push(next); html = next; child = { html: next }; } };
  const root = { querySelector(selector) {
    if (selector === "[data-subdub-settings-rows]") return region;
    if (selector === '[data-subdub-mode-select][aria-selected="true"]') return { getAttribute(name) {
      assert.equal(name, "data-subdub-mode-select"); return "TRANSLATED_SUBTITLE"; } };
    throw Error("unexpected summary selector: " + selector);
  }, getAttribute(name) { assert.equal(name, "lang"); return "en"; } };
  assert.equal(env.api.update(root), true); assert.equal(writes.length, 1);
  assert.equal(value(html, "target_language_custom"), "pt-BR");
  const pressedEdit = child;
  for (const event of ["input", "change", "change"]) {
    assert.equal(env.api.update(root), true, event); assert.equal(writes.length, 1, event); assert.equal(child, pressedEdit, event);
  }
  env.drafts.get("/subdub").shared.target_language_custom = "ko-KR";
  assert.equal(env.api.update(root), true); assert.equal(writes.length, 2); assert.notEqual(child, pressedEdit);
  assert.equal(value(html, "target_language_custom"), "ko-KR"); const changedChild = child;
  assert.equal(env.api.update(root), true); assert.equal(writes.length, 2); assert.equal(child, changedChild);
  assert.equal(env.api.update(root, "DUBBING_ONLY"), true); assert.equal(writes.length, 3); assert.notEqual(child, changedChild);
  assert.equal(value(html, "voice_lane"), "Uploaded voice with consent"); assert.equal(value(html, "original_volume"), "0%");
  assert.equal(value(html, "dubbing_volume"), "200%"); assert.equal(value(html, "target_language_custom"), "ko-KR");
  const modeChild = child;
  assert.equal(env.api.update(root, "DUBBING_ONLY"), true); assert.equal(writes.length, 3); assert.equal(child, modeChild);
});

test("valid Edit focuses before one instant center scroll and invalid or disabled targets never scroll", () => {
  for (const [mode] of modes) {
    const { api } = create(mode), f = fixture(mode), key = mode === "DUBBING_ONLY" ? "target_language" : "subtitle_position";
    const target = f.targets[key], calls = [];
    target.scrollIntoView = function (...args) {
      assert.equal(this, target); assert.deepEqual(f.log, [target], "focus precedes scroll");
      calls.push(args); f.log.push("scroll");
    };
    assert.equal(api.focus(f.edit(key)), true);
    assert.deepEqual(f.log, [target, "scroll"]);
    assert.deepEqual(calls, [[{ block: "center", inline: "nearest", behavior: "instant" }]]);
    f.log.length = 0; calls.length = 0;
    assert.equal(api.focus(f.edit("unsupported")), false); assert.deepEqual(f.log, []); assert.deepEqual(calls, []);
    target.disabled = true;
    assert.equal(api.focus(f.edit(key)), false); assert.deepEqual(f.log, []); assert.deepEqual(calls, []);
    target.disabled = false; target.inheritedDisabled = true;
    assert.equal(api.focus(f.edit(key)), false); assert.deepEqual(f.log, []); assert.deepEqual(calls, []);
  }
});
