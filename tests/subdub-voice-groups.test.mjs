import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const source = readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const start = source.indexOf("  const SUBDUB_PRODUCT_MODES = Object.freeze({");
const end = source.indexOf("\n  function renderDocumentHub", start);
const companion = source.indexOf("  function subDubVoiceCompanionUrl(");
assert.ok(start >= 0 && end > start && companion >= 0, "real renderer boundaries exist");
const renderer = source.slice(companion, source.indexOf("\n  }", companion) + 4) + "\n" + source.slice(start, end);
const escapeHtml = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
const decode = (value) => value.replaceAll("&quot;", '"').replaceAll("&#39;", "'")
  .replaceAll("&lt;", "<").replaceAll("&gt;", ">").replaceAll("&amp;", "&");
const modes = [["DUBBING_ONLY", "dubbing_only", "dub"], ["SUBTITLE_PLUS_DUBBING", "subtitle_plus_dubbing", "combo"]];
const lanes = ["default_female", "default_male", "saved_voice", "custom_voice", "auto_two", "auto_multi_3_8", "smart_multi"];
const groupKeys = ["default", "saved", "add", "auto"];
const members = [["default_female", "default_male"], ["saved_voice"], ["custom_voice"], ["auto_two", "auto_multi_3_8", "smart_multi"]];
const titles = {
  vi: ["Mặc định", "Đã lưu", "Thêm giọng", "Tự động thông minh"],
  en: ["Default", "Saved voices", "Add voice", "Smart automation"],
  zh: ["默认音色", "已保存", "添加音色", "智能自动"]
};
const compact = {
  vi: ["Nữ", "Nam", "Thư viện giọng", "Giọng tự thêm", "Auto 2", "3–8 người nói", "Smart Multi"],
  en: ["Female", "Male", "Voice Library", "Uploaded voice", "Auto 2", "3–8 speakers", "Smart Multi"],
  zh: ["女声", "男声", "音色库", "自定义音色", "自动双人", "3–8 位说话人", "Smart Multi"]
};
const full = {
  vi: ["Giọng nữ mặc định", "Giọng nam mặc định", "Giọng đã lưu trong Thư viện giọng", "Giọng tự thêm có xác nhận quyền sử dụng", "Auto 2 · tự nhận diện hai người nói", "Auto Multi · tự nhận diện 3–8 người nói", "Smart Multi · phân bổ nhiều giọng thông minh"],
  en: ["Default female voice", "Default male voice", "Saved voice from Voice Library", "Uploaded voice with consent", "Auto 2 · detect two speakers", "Auto Multi · detect 3–8 speakers", "Smart Multi · intelligent multi-voice mapping"],
  zh: ["默认女声", "默认男声", "音色库中的已保存音色", "已确认授权的自定义音色", "自动双人 · 识别两位说话人", "自动多人 · 识别 3–8 位说话人", "Smart Multi · 智能分配多人音色"]
};
function renderSubDub(url, locale = "vi", wallet = { balance_xu: 246 }, draft = null) {
  const parsed = new URL(url, "https://app.example");
  const render = new Function("window", "interfaceLocaleFor", "safeText", "badge", "renderHero", "transientFormDrafts",
    renderer + "\nreturn renderSubDubHub;")(
    { location: { search: parsed.search } }, (context) => context?.locale || locale, escapeHtml,
    (state) => '<span data-test-badge="' + escapeHtml(state) + '">' + escapeHtml(state) + "</span>",
    (page) => "<header><h1>" + escapeHtml(page.title) + "</h1></header>",
    new Map(draft ? [["/subdub", draft]] : []));
  return render({ title: "SubDub" }, { locale, wallet });
}
const attr = (tag, name) => {
  const match = tag.match(new RegExp('(?:^|\\s)' + name + '="([^"]*)"'));
  return match ? decode(match[1]) : null;
};
const boolean = (tag, name) => new RegExp("(?:^|\\s)" + name + "(?=\\s|/?>)").test(tag);
const tags = (html, tag) => Array.from(html.matchAll(new RegExp("<(?:" + tag + ")\\b[^>]*>", "g")), (match) => match[0]);
const text = (html) => decode(html.replace(/<[^>]+>/g, "")).trim();
function elements(html, tag) {
  const stack = [], result = [];
  for (const match of html.matchAll(new RegExp("</?" + tag + "\\b[^>]*>", "g"))) {
    if (!match[0].startsWith("</")) stack.push({ start: match.index, open: match[0], from: match.index + match[0].length });
    else {
      const item = stack.pop();
      assert.ok(item, "balanced " + tag + " closing tag");
      result.push({ ...item, inner: html.slice(item.from, match.index), html: html.slice(item.start, match.index + match[0].length) });
    }
  }
  assert.equal(stack.length, 0, "balanced " + tag + " opening tags");
  return result.sort((a, b) => a.start - b.start);
}
function panel(html, key, active = true) {
  const found = elements(html, "section").filter((item) => attr(item.open, "data-subdub-mode-panel") === key);
  assert.equal(found.length, 1, "one exact " + key + " panel");
  if (active) {
    assert.equal(boolean(found[0].open, "hidden"), false);
    assert.equal(attr(found[0].open, "aria-hidden"), "false");
  }
  return found[0].html;
}
const groups = (html) => elements(html, "div").filter((item) => attr(item.open, "data-subdub-voice-group") !== null);
const choices = (html) => elements(html, "label").filter((item) => attr(item.open, "data-subdub-voice-lane") !== null);
const radios = (html) => tags(html, "input").filter((tag) => boolean(tag, "data-subdub-voice-lane-input"));
function setting(html, key) {
  const found = elements(html, "span").filter((item) => attr(item.open, "data-subdub-setting") === key);
  assert.equal(found.length, 1, "one actual review span for " + key);
  return text(found[0].inner);
}
const draftFor = (lane) => ({ shared: { voice_lane: lane, target_language: "ja", target_language_custom: "pt-BR",
  original_volume: "0", dubbing_volume: "200" }, modes: { DUBBING_ONLY: {}, SUBTITLE_PLUS_DUBBING: {} } });

test("each voice panel exposes four localized semantic groups with unique linked heading IDs", () => {
  for (const locale of ["vi", "en", "zh"]) for (const [key, query, suffix] of modes) {
    const html = renderSubDub("/subdub?mode=" + query, locale), active = panel(html, key), items = groups(active);
    assert.equal(items.length, 4, locale + "/" + key + " has four semantic groups");
    assert.equal(tags(active, "fieldset").filter((tag) => boolean(tag, "data-subdub-voice-grouped")).length, 1);
    assert.deepEqual(items.map((item) => attr(item.open, "data-subdub-voice-group")), groupKeys);
    const ids = tags(html, "[a-z][a-z0-9]*").map((tag) => attr(tag, "id")).filter((id) => id !== null);
    assert.equal(new Set(ids).size, ids.length, "all rendered IDs are unique");
    items.forEach((item, index) => {
      const id = "subdub-voice-group-title-" + groupKeys[index] + "-" + suffix;
      assert.equal(attr(item.open, "id"), "subdub-voice-group-" + groupKeys[index] + "-" + suffix);
      assert.equal(attr(item.open, "role"), "group");
      assert.equal(attr(item.open, "aria-labelledby"), id);
      const heading = elements(item.inner, "p").filter((entry) => attr(entry.open, "id") === id);
      assert.equal(heading.length, 1); assert.equal(text(heading[0].inner), titles[locale][index]);
      assert.equal(attr(heading[0].open, "tabindex"), null);
    });
  }
});

test("group membership retains 2/1/1/3 lane order, native input names, one selection and full ARIA names", () => {
  for (const locale of ["vi", "en", "zh"]) for (const [key, query, suffix] of modes) {
    const active = panel(renderSubDub("/subdub?mode=" + query, locale), key), items = groups(active);
    assert.equal(items.length, 4);
    assert.deepEqual(items.map((item) => radios(item.html).map((tag) => attr(tag, "value"))), members);
    const inputs = radios(active);
    assert.deepEqual(inputs.map((tag) => attr(tag, "value")), lanes);
    assert.deepEqual(inputs.map((tag) => attr(tag, "name")), Array(7).fill("subdub_voice_lane_" + suffix));
    assert.ok(inputs.every((tag) => attr(tag, "type") === "radio"));
    assert.deepEqual(inputs.filter((tag) => boolean(tag, "checked")).map((tag) => attr(tag, "value")), ["default_female"]);
    assert.deepEqual(inputs.map((tag) => attr(tag, "aria-label")), full[locale]);
    assert.deepEqual(choices(active).filter((item) => attr(item.open, "class").split(/\s+/).includes("is-selected"))
      .map((item) => attr(item.open, "data-subdub-voice-lane")), ["default_female"]);
  }
});

test("compact choice text stays inside each full accessible name and all seven review names remain literal", () => {
  for (const locale of ["vi", "en", "zh"]) for (const [key, query] of modes) for (const [index, lane] of lanes.entries()) {
    const html = renderSubDub("/subdub?mode=" + query, locale, { balance_xu: 246 }, draftFor(lane));
    const options = choices(panel(html, key));
    assert.equal(options.length, 7);
    options.forEach((item, position) => {
      assert.equal(text(elements(item.inner, "strong")[0].inner), compact[locale][position]);
      assert.equal(attr(radios(item.html)[0], "aria-label"), full[locale][position]);
      assert.ok(full[locale][position].toLocaleLowerCase().includes(compact[locale][position].toLocaleLowerCase()));
    });
    assert.equal(setting(html, "voice_lane"), full[locale][index], locale + "/" + key + "/" + lane + " review");
  }
});

test("callback mapping, single shared note/link, inert Smart/speaker tail and disabled source/CTA survive grouping", () => {
  for (const locale of ["vi", "en", "zh"]) for (const [key, query, suffix] of modes) {
    const html = renderSubDub("/subdub?mode=" + query, locale), active = panel(html, key);
    const callbacks = choices(active).map((item) => [attr(item.open, "data-subdub-voice-lane"), attr(item.open, "data-subdub-callback")])
      .filter(([, callback]) => callback !== null);
    assert.deepEqual(callbacks, [["auto_two", "videodub|voice|auto_speaker_gender"],
      ["auto_multi_3_8", "videodub|voice|auto_multi_speaker"], ["smart_multi", "videodub|voice|auto_smart_multivoice"]]);
    const note = elements(active, "p").filter((item) => attr(item.open, "id") === "subdub-voice-lane-note-" + suffix);
    const links = tags(active, "a").filter((tag) => boolean(tag, "data-subdub-voice-library-link"));
    assert.equal(note.length, 1); assert.ok(text(note[0].inner).length > 0); assert.equal(links.length, 1);
    const outer = tags(active, "fieldset").find((tag) => attr(tag, "class") === "portal-subdub-voice-lanes");
    assert.equal(attr(outer, "aria-describedby"), "subdub-voice-lane-note-" + suffix);
    const smart = elements(active, "fieldset").filter((item) => boolean(item.open, "data-subdub-smart-multi"));
    const speakers = elements(active, "div").filter((item) => boolean(item.open, "data-subdub-speaker-map"));
    assert.equal(smart.length, 1); assert.equal(speakers.length, 1);
    for (const item of [...smart, ...speakers]) {
      assert.equal(attr(item.open, "data-status"), "guarded");
      assert.equal(tags(item.html, "input|button|select").length, 0);
    }
    assert.equal(attr(smart[0].open, "data-subdub-callback"), "videodub|voice|auto_smart_multivoice");
    assert.ok(note[0].start < active.indexOf(links[0]) && active.indexOf(links[0]) < smart[0].start && smart[0].start < speakers[0].start);
    assert.equal(groups(active).some((item) => item.html.includes(note[0].open) || item.html.includes(links[0])), false);
    const file = tags(html, "input").find((tag) => attr(tag, "id") === "subdub-source-file");
    const cta = tags(html, "button").find((tag) => (attr(tag, "class") || "").split(/\s+/).includes("portal-subdub-cta"));
    assert.ok(file && boolean(file, "disabled")); assert.ok(cta && boolean(cta, "disabled"));
  }
});

test("subtitle-only active panels expose no voice groups while both hidden voice panels retain eight unique groups and fourteen radios", () => {
  for (const locale of ["vi", "en", "zh"]) for (const key of ["SUBTITLE_ONLY", "TRANSLATED_SUBTITLE"]) {
    const html = renderSubDub("/subdub?mode=" + key.toLowerCase(), locale), active = panel(html, key);
    assert.equal(groups(active).length, 0); assert.equal(radios(active).length, 0);
    assert.equal(groups(html).length, 8); assert.equal(radios(html).length, 14);
    for (const [voiceKey] of modes) {
      const hidden = panel(html, voiceKey, false);
      assert.equal(boolean(tags(hidden, "section")[0], "hidden"), true);
      assert.equal(attr(tags(hidden, "section")[0], "aria-hidden"), "true");
      assert.equal(groups(hidden).length, 4); assert.equal(radios(hidden).length, 7);
    }
    const ids = groups(html).flatMap((item) => [attr(item.open, "id"), attr(item.open, "aria-labelledby")]);
    assert.equal(new Set(ids).size, 16); assert.equal(ids.some((id) => id === null), false);
  }
});

test("saved and custom drafts preserve selection, Japanese/custom ISO, 0/200 mix reviews and exact Voice return modes", () => {
  for (const locale of ["vi", "en", "zh"]) for (const [key, query] of modes) for (const lane of ["saved_voice", "custom_voice"]) {
    const html = renderSubDub("/subdub?mode=" + query, locale, { balance_xu: 246 }, draftFor(lane)), active = panel(html, key);
    assert.deepEqual(radios(active).filter((tag) => boolean(tag, "checked")).map((tag) => attr(tag, "value")), [lane]);
    assert.deepEqual(choices(active).filter((item) => attr(item.open, "class").split(/\s+/).includes("is-selected"))
      .map((item) => attr(item.open, "data-subdub-voice-lane")), [lane]);
    assert.equal(setting(html, "voice_lane"), full[locale][lane === "saved_voice" ? 2 : 3]);
    const select = elements(active, "select").find((item) => attr(item.open, "name") === "target_language");
    assert.deepEqual(tags(select.inner, "option").filter((tag) => boolean(tag, "selected")).map((tag) => attr(tag, "value")), ["ja"]);
    const custom = tags(active, "input").find((tag) => attr(tag, "name") === "target_language_custom");
    assert.equal(attr(custom, "value"), "pt-BR"); assert.equal(setting(html, "target_language_custom"), "pt-BR");
    for (const [kind, value, max] of [["original", "0", "100"], ["dubbing", "200", "200"]]) {
      const controls = tags(active, "input").filter((tag) => attr(tag, "data-subdub-local-volume") === kind);
      assert.deepEqual(controls.map((tag) => attr(tag, "type")).sort(), ["number", "range"]);
      for (const tag of controls) {
        assert.equal(attr(tag, "value"), value); assert.equal(attr(tag, "min"), "0"); assert.equal(attr(tag, "max"), max);
      }
      const output = elements(active, "output").filter((item) => attr(item.open, "data-subdub-volume-output") === kind);
      assert.equal(output.length, 1); assert.equal(text(output[0].inner), value + "%");
      assert.equal(setting(html, kind + "_volume"), value + "%");
    }
    const link = tags(active, "a").filter((tag) => boolean(tag, "data-subdub-voice-library-link"));
    assert.equal(link.length, 1);
    const url = new URL(attr(link[0], "href"), "https://app.example");
    assert.equal(url.pathname, lane === "custom_voice" ? "/voice/clone" : "/voice/saved");
    assert.equal(url.searchParams.get("return_to"), "/subdub?mode=" + query);
  }
});
