import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const start = source.indexOf("  const SUBDUB_PRODUCT_MODES = Object.freeze({"), end = source.indexOf("\n  function renderDocumentHub", start);
const companion = source.indexOf("  function subDubVoiceCompanionUrl("), companionEnd = source.indexOf("\n  }", companion);
assert.ok(start >= 0 && end > start && companion >= 0 && companionEnd > companion, "real renderer boundaries");
const renderer = source.slice(companion, companionEnd + 4) + "\n" + source.slice(start, end);
const escape = (v) => String(v ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
const decode = (v) => v.replaceAll("&quot;", '"').replaceAll("&#39;", "'").replaceAll("&lt;", "<").replaceAll("&gt;", ">").replaceAll("&amp;", "&");
const modes = [["SUBTITLE_ONLY", "subtitle_only"], ["TRANSLATED_SUBTITLE", "translated_subtitle"], ["DUBBING_ONLY", "dubbing_only"], ["SUBTITLE_PLUS_DUBBING", "subtitle_plus_dubbing"]];
const locales = ["vi", "en", "zh"], lanes = ["default_female", "default_male", "saved_voice", "custom_voice", "auto_two", "auto_multi_3_8", "smart_multi"];
const pending = { vi: "Thiết lập mở sau khi phiên đăng nhập được xác nhận.", en: "Settings open after your sign-in session is confirmed.", zh: "登录状态确认后即可编辑设置。" };
const ready = { authenticated: true, csrfToken: "unit-session" };
const draft = () => ({ shared: { voice_lane: "custom_voice", target_language: "ja", target_language_custom: "pt-BR", original_volume: "0", dubbing_volume: "200" },
  modes: { DUBBING_ONLY: {}, SUBTITLE_PLUS_DUBBING: {} } });
function harness(query = "dubbing_only", saved = draft()) {
  const drafts = new Map([["/subdub", structuredClone(saved)], ["/unrelated", { keep: "unchanged" }]]);
  const win = { location: { search: "?mode=" + query, href: "https://app.example/subdub?mode=" + query },
    fetch() { throw Error("unexpected request"); }, history: { replaceState() { throw Error("unexpected history write"); } } };
  const api = new Function("window", "interfaceLocaleFor", "safeText", "badge", "renderHero", "transientFormDrafts",
    renderer + '\nreturn { render: renderSubDubHub, markup: typeof subDubAuthoringMarkup === "function" ? subDubAuthoringMarkup : null, update: updateSubDubSettingsSummary };')(
    win, (context) => context.locale, escape, () => "", () => "", drafts);
  return { ...api, drafts, win, render: (context) => api.render({ title: "SubDub" }, context) };
}
const attr = (tag, name) => { const m = tag.match(new RegExp('(?:^|\\s)' + name + '="([^"]*)"')); return m ? decode(m[1]) : null; };
const openings = (html, names) => Array.from(html.matchAll(new RegExp("<(?:" + names + ')\\b(?:"[^"]*"|\\\'[^\\\']*\\\'|[^\\\'">])*>', "gi")), (m) => m[0]);
const controls = (html) => openings(html, "button|input|select|textarea");
const disabled = (tag) => /(?:^|\s)disabled(?=\s|=|\/?>)/i.test(tag.replace(/"[^"]*"|'[^']*'/g, ""));
const flag = (html) => attr(openings(html, "article")[0], "data-subdub-authoring-ready");
const status = (html) => Array.from(html.matchAll(/<p\b[^>]*data-subdub-authoring-session-status[^>]*>([^<]*)<\/p>/g));
const inputRadios = (html) => openings(html, "input").filter((tag) => /\sdata-subdub-voice-lane-input(?:\s|>)/.test(tag));
function panel(html, key, active = false) {
  const found = Array.from(html.matchAll(/<section\b[^>]*data-subdub-mode-panel="([^"]+)"[^>]*>[\s\S]*?<\/section>/g)).filter((m) => m[1] === key);
  assert.equal(found.length, 1, "one exact " + key + " panel");
  if (active) { const open = found[0][0].split(">")[0] + ">"; assert.equal(attr(open, "aria-hidden"), "false"); assert.ok(!/\shidden(?=\s|>)/.test(open)); }
  return found[0][0];
}
function review(html, key) {
  const found = Array.from(html.matchAll(/<span\b[^>]*data-subdub-setting="([^"]+)"[^>]*>([^<]*)<\/span>/g)).filter((m) => m[1] === key);
  assert.equal(found.length, 1, "one review span " + key); return decode(found[0][2]);
}
function summary(dataset) {
  const writes = []; let html = "", child = null;
  const region = { get innerHTML() { return html; }, set innerHTML(next) { html = next; child = { html: next }; writes.push(next); } };
  const button = { getAttribute(name) { assert.equal(name, "data-subdub-mode-select"); return "DUBBING_ONLY"; } };
  const root = { dataset, getAttribute(name) { assert.equal(name, "lang"); return "en"; }, querySelector(selector) {
    if (selector === "[data-subdub-settings-rows]") return region;
    if (selector === '[data-subdub-mode-select][aria-selected="true"]') return button;
    throw Error("unexpected summary selector: " + selector);
  } };
  return { root, region, writes, child: () => child };
}

test("all invalid session predicates across twelve views keep every native authoring control disabled with one localized reason", () => {
  const sessions = [undefined, null, {}, { authenticated: false, csrfToken: "x" }, { authenticated: "true", csrfToken: "x" },
    { authenticated: 1, csrfToken: "x" }, { authenticated: true }, { authenticated: true, csrfToken: "" },
    { authenticated: true, csrfToken: null }, { authenticated: true, csrfToken: 1 }, { authenticated: true, csrfToken: new String("x") }];
  for (const [, query] of modes) for (const locale of locales) for (const session of sessions) {
    const html = harness(query).render({ locale, session }), tags = controls(html), reasons = status(html);
    assert.ok(tags.length > 0); assert.equal(tags.filter((tag) => !disabled(tag)).length, 0, query + "/" + locale);
    assert.equal(flag(html), "false"); assert.equal(reasons.length, 1);
    assert.equal(reasons[0][1], pending[locale]); assert.equal(attr(reasons[0][0], "role"), "status");
  }
});

test("genuine sessions retain twelve ready views with only three permanent guards, seven lanes per voice panel and public anchors", () => {
  for (const [key, query] of modes) for (const locale of locales) for (const token of ["unit-session", " "]) {
    const html = harness(query).render({ locale, session: { authenticated: true, csrfToken: token } }), tags = controls(html);
    assert.equal(flag(html), "true"); assert.equal(status(html).length, 0);
    const guarded = tags.filter(disabled);
    assert.equal(guarded.length, 3);
    assert.deepEqual(guarded.map((tag) => attr(tag, "id") || attr(tag, "class")), ["subdub-source-file", "subdub-source-lang", "portal-button portal-subdub-cta"]);
    assert.ok(tags.filter((tag) => !guarded.includes(tag)).every((tag) => !disabled(tag)));
    const tabs = openings(html, "button").filter((tag) => attr(tag, "data-subdub-mode-select") !== null);
    assert.deepEqual(tabs.map((tag) => attr(tag, "data-subdub-mode-select")), ["SUBTITLE_ONLY", "TRANSLATED_SUBTITLE", "DUBBING_ONLY", "SUBTITLE_PLUS_DUBBING"]);
    assert.equal(inputRadios(html).length, 14);
    for (const voiceKey of ["DUBBING_ONLY", "SUBTITLE_PLUS_DUBBING"]) {
      const voice = panel(html, voiceKey), radios = inputRadios(voice);
      assert.deepEqual(radios.map((tag) => attr(tag, "value")), lanes); assert.ok(radios.every((tag) => !disabled(tag)));
      const callbacks = openings(voice, "label").map((tag) => attr(tag, "data-subdub-callback")).filter((value) => value !== null);
      assert.deepEqual(callbacks, ["videodub|voice|auto_speaker_gender", "videodub|voice|auto_multi_speaker", "videodub|voice|auto_smart_multivoice"]);
    }
    if (key === "SUBTITLE_ONLY" || key === "TRANSLATED_SUBTITLE") assert.equal(inputRadios(panel(html, key, true)).length, 0);
    const links = openings(html, "a").map((tag) => attr(tag, "href"));
    for (const href of ["/subtitle/formats", "/subtitle/assets", "/subtitle-studio"]) assert.ok(links.includes(href), href);
    assert.ok(openings(html, "a").every((tag) => !disabled(tag)));
  }
});

test("pure readiness markup handles all four tag families, quoted greater-than/disabled text and strict idempotent gating", () => {
  const { markup } = harness(); assert.equal(typeof markup, "function", "real readiness markup helper exists");
  const cases = [
    ['<button title="disabled > text">Go</button>', '<button disabled title="disabled > text">Go</button>'],
    ["<input title='disabled > text' value='a > b'>", "<input disabled title='disabled > text' value='a > b'>"],
    ['<select id="s"><option value="x" selected>X</option></select>', '<select disabled id="s"><option value="x" selected>X</option></select>'],
    ['<textarea title="> disabled">A &lt; B</textarea>', '<textarea disabled title="> disabled">A &lt; B</textarea>'],
    ['<button disabled id="b">B</button>', '<button disabled id="b">B</button>'],
    ['<input disabled="disabled" value="x">', '<input disabled="disabled" value="x">'],
    ["<select disabled='disabled'><option>X</option></select>", "<select disabled='disabled'><option>X</option></select>"],
    ['<a href="/voice/saved" title="disabled >">A &gt; B</a><span>disabled &lt;input&gt;</span>', '<a href="/voice/saved" title="disabled >">A &gt; B</a><span>disabled &lt;input&gt;</span>']
  ];
  for (const [input, expected] of cases) {
    assert.equal(markup(input, true), input);
    for (const state of [false, undefined, null, 1, "true", {}]) assert.equal(markup(input, state), expected);
    assert.equal(markup(expected, false), expected, "no duplicate disabled attribute or second transformation");
  }
});

test("actual summary update gates Edit with false/missing/true dataset and retains child identity on identical generated rows", () => {
  const h = harness(), s = summary({ subdubAuthoringReady: "false" });
  assert.equal(h.update(s.root), true); assert.equal(s.writes.length, 1);
  assert.equal(controls(s.region.innerHTML).length, 6); assert.ok(controls(s.region.innerHTML).every(disabled));
  const pendingChild = s.child();
  assert.equal(h.update(s.root), true); assert.equal(s.writes.length, 1); assert.equal(s.child(), pendingChild);
  delete s.root.dataset;
  assert.equal(h.update(s.root), true); assert.equal(s.writes.length, 1); assert.equal(s.child(), pendingChild);
  s.root.dataset = { subdubAuthoringReady: "true" };
  assert.equal(h.update(s.root), true); assert.equal(s.writes.length, 2); assert.notEqual(s.child(), pendingChild);
  assert.ok(controls(s.region.innerHTML).every((tag) => !disabled(tag))); const readyChild = s.child();
  assert.equal(h.update(s.root), true); assert.equal(s.writes.length, 2); assert.equal(s.child(), readyChild);
  s.root.dataset = { subdubAuthoringReady: true };
  assert.equal(h.update(s.root), true); assert.equal(s.writes.length, 3); assert.ok(controls(s.region.innerHTML).every(disabled));
  const strictChild = s.child(); assert.equal(h.update(s.root), true); assert.equal(s.writes.length, 3); assert.equal(s.child(), strictChild);
});

test("actual render/markup/update leave signed and anonymous draft, session and window unchanged with exact active Dub values and review", () => {
  for (const session of [ready, null, { authenticated: false, csrfToken: "unit-session" }]) {
    const h = harness(), context = { locale: "en", session }; assert.equal(typeof h.markup, "function");
    const before = JSON.stringify({ map: [...h.drafts], window: h.win, context }), html = h.render(context);
    assert.equal(h.markup(html, true), html);
    const s = summary({ subdubAuthoringReady: session === ready ? "true" : "false" }); assert.equal(h.update(s.root), true);
    assert.equal(JSON.stringify({ map: [...h.drafts], window: h.win, context }), before);
    const active = panel(html, "DUBBING_ONLY", true), radios = inputRadios(active);
    assert.deepEqual(radios.filter((tag) => /\schecked(?=\s|>)/.test(tag)).map((tag) => attr(tag, "value")), ["custom_voice"]);
    const select = active.match(/<select\b[^>]*name="target_language"[^>]*>([\s\S]*?)<\/select>/);
    assert.ok(select); assert.deepEqual(openings(select[1], "option").filter((tag) => /\sselected(?=\s|>)/.test(tag)).map((tag) => attr(tag, "value")), ["ja"]);
    const custom = openings(active, "input").filter((tag) => attr(tag, "name") === "target_language_custom");
    assert.equal(custom.length, 1); assert.equal(attr(custom[0], "value"), "pt-BR");
    for (const [kind, expected] of [["original", "0"], ["dubbing", "200"]]) {
      const inputs = openings(active, "input").filter((tag) => attr(tag, "data-subdub-local-volume") === kind);
      assert.deepEqual(inputs.map((tag) => attr(tag, "type")).sort(), ["number", "range"]);
      assert.ok(inputs.every((tag) => attr(tag, "value") === expected));
    }
    for (const [key, expected] of [["voice_lane", "Uploaded voice with consent"], ["target_language", "Japanese"], ["target_language_custom", "pt-BR"], ["original_volume", "0%"], ["dubbing_volume", "200%"]]) {
      assert.equal(review(html, key), expected); assert.equal(review(s.region.innerHTML, key), expected);
    }
  }
});

test("pending text is exact while ready/unready hierarchy, existing fieldsets, values, IDs and anchors differ only by declared readiness markup", () => {
  for (const [, query] of modes) for (const locale of locales) {
    const h = harness(query), a = h.render({ locale, session: null }), b = h.render({ locale, session: ready });
    assert.equal(flag(a), "false"); assert.equal(flag(b), "true"); assert.equal(status(a).length, 1); assert.equal(status(a)[0][1], pending[locale]);
    assert.equal(status(b).length, 0);
    const expectedControls = controls(b); let index = 0;
    const normalize = (html, pendingState) => html.replace(/ data-subdub-authoring-ready="(?:true|false)"/, "")
      .replace(/<p class="portal-form-note" role="status" data-subdub-authoring-session-status>[^<]*<\/p>/, "")
      .replace(/<(?:button|input|select|textarea)\b(?:"[^"]*"|'[^']*'|[^'">])*>/gi, (tag) => {
        const original = expectedControls[index++]; assert.ok(original);
        return pendingState && !disabled(original) ? tag.replace(/\sdisabled(?=\s|\/?>)/i, "") : tag;
      }).replace(/\s+/g, " ").trim();
    const normalizedA = normalize(a, true); assert.equal(index, expectedControls.length); index = 0;
    assert.equal(normalizedA, normalize(b, false)); assert.equal(index, expectedControls.length);
    assert.ok(openings(b, "fieldset").length > 0); assert.deepEqual(openings(a, "fieldset"), openings(b, "fieldset"));
    assert.deepEqual(openings(a, "a"), openings(b, "a"));
    assert.deepEqual(Array.from(a.matchAll(/\bid="[^"]*"/g), (m) => m[0]), Array.from(b.matchAll(/\bid="[^"]*"/g), (m) => m[0]));
  }
});
