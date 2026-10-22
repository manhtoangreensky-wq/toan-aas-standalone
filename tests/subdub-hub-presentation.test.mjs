import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const helperStart = portalSource.indexOf("  function updateSubDubModeSelection(");
const helperEnd = portalSource.indexOf("\n  function renderSubDubHub", helperStart);
const rendererStart = portalSource.indexOf("  const SUBDUB_PRODUCT_MODES = Object.freeze({");
const rendererEnd = portalSource.indexOf("\n  function renderDocumentHub", rendererStart);

assert.notEqual(helperStart, -1, "SubDub local presentation handlers are present");
assert.notEqual(helperEnd, -1, "SubDub local presentation handler boundary is present");
assert.notEqual(rendererStart, -1, "SubDub renderer source is present");
assert.notEqual(rendererEnd, -1, "SubDub renderer boundary is present");

const helperSource = portalSource.slice(helperStart, helperEnd);
const companionStart = portalSource.indexOf("  function subDubVoiceCompanionUrl(");
assert.notEqual(companionStart, -1, "SubDub companion URL helper is present");
const companionSource = portalSource.slice(companionStart, portalSource.indexOf("\n  }", companionStart) + 4);
const rendererSource = companionSource + "\n" + portalSource.slice(rendererStart, rendererEnd);
const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#39;");

const renderSubDubHelpers = new Function("transientFormDrafts", "safeText", `${rendererSource}\nreturn { updateSubDubModeSelection, updateSubDubLocalVolume, updateSubDubVoiceLaneSelection, handleSubDubModeKeydown };`)(new Map(), escapeHtml);

function renderSubDub(url, locale = "vi", wallet = { balance_xu: 246 }, draft = null) {
  const parsed = new URL(url, "https://app.example");
  const browserWindow = { location: { search: parsed.search } };
  const render = new Function(
    "window",
    "interfaceLocaleFor",
    "safeText",
    "badge",
    "renderHero",
    "transientFormDrafts",
    `${rendererSource}\nreturn { renderSubDubHub, updateSubDubModeSelection, updateSubDubLocalVolume, updateSubDubVoiceLaneSelection };`
  )(
    browserWindow,
    (context) => context?.locale || locale,
    escapeHtml,
    (state) => `<span data-test-badge="${escapeHtml(state)}">${escapeHtml(state)}</span>`,
    (page) => `<header class="test-route-hero"><h1>${escapeHtml(page?.title || "SubDub")}</h1><p>${escapeHtml(page?.description || "")}</p></header>`,
    new Map(draft ? [["/subdub", draft]] : [])
  );

  return render.renderSubDubHub({ title: "SubDub" }, { locale, wallet });
}

test("SubDub shared draft keeps compatible language, voice and volume values across modes and rerender", () => {
  const draft = {
    shared: { target_language: "en", target_language_custom: "", original_volume: "0", dubbing_volume: "200", voice_lane: "default_male", subtitle_position: "top_center", sub_display_type: "bilingual" },
    modes: { DUBBING_ONLY: { target_language: "en" }, SUBTITLE_PLUS_DUBBING: {} }
  };
  const dubbing = renderSubDub("/subdub?mode=dubbing_only", "vi", { balance_xu: 246 }, draft);
  const combo = renderSubDub("/subdub?mode=subtitle_plus_dubbing", "vi", { balance_xu: 246 }, draft);
  for (const html of [dubbing, combo]) {
    assert.match(html, /<option value="en" selected>Tiếng Anh<\/option>/);
    assert.match(html, /data-subdub-local-volume="original"[^>]*value="0"/);
    assert.match(html, /data-subdub-local-volume="dubbing"[^>]*value="200"/);
    assert.match(html, /value="default_male"[^>]*checked/);
    assert.match(html, /<option value="top_center" selected>/);
  }
  assert.match(combo, /data-subdub-mode-select="SUBTITLE_PLUS_DUBBING"[^>]*aria-selected="true"/);
});

test("SubDub mode selection stays on one screen and exposes all four choices", () => {
  const html = renderSubDub("/subdub?mode=dubbing_only");

  assert.equal((html.match(/data-subdub-mode-select=/g) || []).length, 4);
  assert.equal((html.match(/data-subdub-mode-panel=/g) || []).length, 4);
  assert.match(html, /role="tablist"[^>]*aria-orientation="horizontal"/);
  assert.equal((html.match(/role="tab"/g) || []).length, 4);
  assert.equal((html.match(/role="tabpanel"/g) || []).length, 4);
  assert.match(html, /data-subdub-mode-select="DUBBING_ONLY"[^>]*aria-selected="true"[^>]*tabindex="0"/);
  assert.match(html, /data-subdub-mode-select="SUBTITLE_ONLY"[^>]*aria-selected="false"[^>]*tabindex="-1"/);
  assert.match(html, /data-subdub-mode-select="DUBBING_ONLY"[^>]*aria-pressed="true"/);
  assert.match(html, /data-subdub-mode-panel="SUBTITLE_ONLY"[^>]*hidden/);
  assert.match(html, /data-subdub-mode-panel="SUBTITLE_ONLY"[^>]*aria-hidden="true"/);
  assert.match(html, /data-subdub-mode-panel="DUBBING_ONLY"[^>]*aria-hidden="false"/);
  assert.doesNotMatch(html, /href="\/subdub\?mode=/);
});

test("dubbing modes expose separate local original and voice volume controls", () => {
  const html = renderSubDub("/subdub?mode=dubbing_only");
  const dubbingPanel = html.match(/data-subdub-mode-panel="DUBBING_ONLY"[\s\S]*?<\/section>/)?.[0] || "";
  const comboPanel = html.match(/data-subdub-mode-panel="SUBTITLE_PLUS_DUBBING"[\s\S]*?<\/section>/)?.[0] || "";
  const subtitlePanel = html.match(/data-subdub-mode-panel="SUBTITLE_ONLY"[\s\S]*?<\/section>/)?.[0] || "";

  for (const panel of [dubbingPanel, comboPanel]) {
    assert.match(panel, /data-subdub-local-volume="original"/);
    assert.match(panel, /data-subdub-local-volume="dubbing"/);
    assert.match(panel, /<output[^>]*>100%<\/output>/);
    assert.match(panel, /data-subdub-local-volume="dubbing"[^>]*max="200"|max="200"[^>]*data-subdub-local-volume="dubbing"/);
    assert.doesNotMatch(panel, /name="(?:original_volume|dubbing_volume)"/);
  }
  assert.doesNotMatch(subtitlePanel, /data-subdub-local-volume=/);
});

test("SubDub renders complete Chinese copy rather than falling back to Vietnamese", () => {
  const html = renderSubDub("/subdub?lang=zh&mode=subtitle_only", "zh");

  assert.match(html, /字幕与配音/);
  assert.match(html, /选择需要的处理方式/);
  assert.doesNotMatch(html, /Trung tâm phụ đề|Chưa có tác vụ/);
});

test("SubDub output area is an honest empty report and execution stays guarded", () => {
  const html = renderSubDub("/subdub?mode=subtitle_plus_dubbing");

  assert.match(html, /data-subdub-stage="4"/);
  assert.match(html, /data-subdub-report-empty/);
  assert.doesNotMatch(html, /portal-subdub-status-guide/);
  assert.match(html, /class="portal-button portal-subdub-cta" type="button" disabled data-status="guarded"/);
  assert.doesNotMatch(html, /data-portal-action="(?:feature-confirm|subdub-submit)"/);
});

test("all twelve locale and mode combinations keep one panel selected and localize the hero", () => {
  const localeCopy = {
    vi: "Chọn phụ đề, lồng tiếng hoặc kết hợp cả hai.",
    en: "Choose subtitles, dubbing, or both.",
    zh: "选择所需的处理方式"
  };
  for (const [locale, expectedCopy] of Object.entries(localeCopy)) {
    for (const mode of ["SUBTITLE_ONLY", "TRANSLATED_SUBTITLE", "DUBBING_ONLY", "SUBTITLE_PLUS_DUBBING"]) {
      const html = renderSubDub(`/subdub?lang=${locale}&mode=${mode.toLowerCase()}`, locale);
      assert.ok(html.includes(expectedCopy), `${locale}/${mode} hero is translated`);
      assert.equal((html.match(/data-subdub-mode-panel="[A-Z_]+" hidden/g) || []).length, 3);
      assert.ok(html.includes(`data-subdub-mode-select="${mode}"`));
      if (locale !== "vi") assert.doesNotMatch(html, /Trung tâm phụ đề tự động|Chưa có báo cáo xử lý|Ngôn ngữ trong tệp gốc|Bạn muốn tạo gì/);
      if (locale === "vi") assert.doesNotMatch(html, /\bmedia\b|\bDubbing\b|\bPlain text\b/);
    }
  }
});

test("subtitle format radio groups remain independent when modes are switched", () => {
  const html = renderSubDub("/subdub");
  for (const group of ["subdub-source-output-format", "subdub-translated-output-format", "subdub-combined-output-format"]) {
    assert.equal((html.match(new RegExp(`name="${group}"[^>]*checked`, "g")) || []).length, 1);
  }
  assert.doesNotMatch(html, /type="radio" name="output_format"/);
});

test("unknown wallet projection stays unknown and legacy mode aliases keep their intent", () => {
  const html = renderSubDub("/subdub", "vi", null);
  assert.match(html, /class="portal-summary-value">—<\/span>/);
  assert.doesNotMatch(html, />0 Xu<\/span>/);
  for (const [alias, mode] of Object.entries({ subtitle: "SUBTITLE_ONLY", translate: "TRANSLATED_SUBTITLE", dub: "DUBBING_ONLY", combo: "SUBTITLE_PLUS_DUBBING" })) {
    assert.match(renderSubDub(`/subdub?mode=${alias}`), new RegExp(`data-subdub-mode-select="${mode}"[^>]*aria-pressed="true"`));
  }
});

test("mode changes update the selected panel, review summary, and query without navigating", () => {
  const parsed = new URL("https://app.example/subdub?lang=vi&mode=subtitle_only#hub");
  const buttons = ["SUBTITLE_ONLY", "TRANSLATED_SUBTITLE", "DUBBING_ONLY", "SUBTITLE_PLUS_DUBBING"].map((key) => ({
    key,
    attributes: {
      "data-subdub-mode-select": key,
      "data-subdub-mode-query": key.toLowerCase(),
      "data-subdub-summary-label": `${key} summary`
    },
    pressed: "false",
    active: false,
    closest() { return page; },
    getAttribute(name) { return this.attributes[name] ?? ""; },
    setAttribute(name, value) { this.attributes[name] = value; if (name === "aria-pressed") this.pressed = value; },
    classList: { toggle(_className, enabled) { this.owner.active = enabled; }, owner: null }
  }));
  buttons.forEach((button) => { button.classList.owner = button; });
  const panels = buttons.map((button) => ({ mode: button.key, hidden: true, attributes: {}, getAttribute(name) { return name === "data-subdub-mode-panel" ? this.mode : this.attributes[name] || ""; }, setAttribute(name, value) { this.attributes[name] = value; } }));
  const summary = { textContent: "" };
  const settings = { innerHTML: "" };
  const page = {
    querySelectorAll(selector) { return selector === "[data-subdub-mode-select]" ? buttons : panels; },
    querySelector(selector) { return selector === "[data-subdub-summary-mode]" ? summary : selector === "[data-subdub-settings-rows]" ? settings : null; },
    getAttribute(name) { return name === "lang" ? "vi" : null; }
  };
  let replacedUrl = "";
  const browserWindow = {
    URL,
    location: { href: parsed.toString() },
    history: { state: null, replaceState(_state, _title, url) { replacedUrl = url; } }
  };

  const selectedButton = buttons[3];
  assert.equal(renderSubDubHelpers.updateSubDubModeSelection(selectedButton, browserWindow), true);
  assert.deepEqual(buttons.map((button) => button.pressed), ["false", "false", "false", "true"]);
  assert.deepEqual(buttons.map((button) => button.active), [false, false, false, true]);
  assert.deepEqual(panels.map((panel) => panel.hidden), [true, true, true, false]);
  assert.equal(summary.textContent, "SUBTITLE_PLUS_DUBBING summary");
  assert.match(settings.innerHTML, /data-subdub-setting="voice_lane"/);
  assert.match(settings.innerHTML, /data-subdub-setting="sub_display_type"/);
  const finalUrl = new URL(replacedUrl);
  assert.equal(finalUrl.pathname, "/subdub");
  assert.equal(finalUrl.searchParams.get("lang"), "vi");
  assert.equal(finalUrl.searchParams.get("mode"), "subtitle_plus_dubbing");
  assert.equal(finalUrl.hash, "#hub");
});

test("SubDub mode tabs support arrow-key navigation without leaving the hub", () => {
  const parsed = new URL("https://app.example/subdub?lang=vi&mode=subtitle_only");
  const buttons = ["SUBTITLE_ONLY", "TRANSLATED_SUBTITLE", "DUBBING_ONLY", "SUBTITLE_PLUS_DUBBING"].map((key, index) => ({
    key,
    attributes: {
      "data-subdub-mode-select": key,
      "data-subdub-mode-query": key.toLowerCase(),
      "data-subdub-summary-label": `${key} summary`,
      "aria-pressed": index === 0 ? "true" : "false",
      "aria-selected": index === 0 ? "true" : "false",
      tabindex: index === 0 ? "0" : "-1"
    },
    focused: false,
    closest() { return page; },
    getAttribute(name) { return this.attributes[name] ?? ""; },
    setAttribute(name, value) { this.attributes[name] = value; },
    focus() { this.focused = true; },
    classList: { toggle() {} }
  }));
  const panels = buttons.map((button, index) => ({
    mode: button.key,
    hidden: index !== 0,
    attributes: { "aria-hidden": index === 0 ? "false" : "true" },
    getAttribute(name) { return name === "data-subdub-mode-panel" ? this.mode : this.attributes[name] ?? ""; },
    setAttribute(name, value) { this.attributes[name] = value; }
  }));
  const summary = { textContent: "SUBTITLE_ONLY summary" };
  const settings = { innerHTML: "" };
  const page = {
    querySelectorAll(selector) {
      return selector === "[data-subdub-mode-select]" ? buttons : panels;
    },
    querySelector(selector) { return selector === "[data-subdub-summary-mode]" ? summary : selector === "[data-subdub-settings-rows]" ? settings : null; },
    getAttribute(name) { return name === "lang" ? "vi" : null; }
  };
  let replacedUrl = "";
  const browserWindow = {
    URL,
    location: { href: parsed.toString() },
    history: { state: null, replaceState(_state, _title, url) { replacedUrl = url; } }
  };
  const press = (fromIndex, key) => {
    let prevented = false;
    const handled = renderSubDubHelpers.handleSubDubModeKeydown(buttons[fromIndex], {
      key,
      preventDefault() { prevented = true; }
    }, browserWindow);
    assert.equal(handled, true, `${key} is handled`);
    assert.equal(prevented, true, `${key} prevents the browser's default tab movement`);
  };
  press(0, "ArrowRight");
  assert.equal(buttons[1].focused, true);
  assert.equal(buttons[1].attributes["aria-selected"], "true");
  assert.equal(buttons[0].attributes["tabindex"], "-1");
  assert.equal(panels[0].hidden, true);
  assert.equal(panels[1].hidden, false);
  assert.match(settings.innerHTML, /data-subdub-setting="target_language"/);
  assert.doesNotMatch(settings.innerHTML, /data-subdub-setting="voice_lane"/);
  assert.equal(new URL(replacedUrl).searchParams.get("mode"), "translated_subtitle");
  press(1, "ArrowDown");
  assert.equal(buttons[2].attributes["aria-selected"], "true");
  press(2, "ArrowLeft");
  assert.equal(buttons[1].attributes["aria-selected"], "true");
  press(1, "ArrowUp");
  assert.equal(buttons[0].attributes["aria-selected"], "true");
  press(2, "Home");
  assert.equal(buttons[0].attributes["aria-selected"], "true");
  press(0, "End");
  assert.equal(buttons[3].focused, true);
  assert.equal(buttons[3].attributes["aria-selected"], "true");
  assert.equal(panels[3].hidden, false);
  assert.equal(new URL(replacedUrl).searchParams.get("mode"), "subtitle_plus_dubbing");
});

test("local volume input updates its visible value only", () => {
  const output = { textContent: "100%" };
  const panel = { querySelector(selector) { return selector.startsWith("[data-subdub-volume-output=") ? output : null; } };
  const input = {
    value: "42",
    closest() { return panel; },
    getAttribute() { return "dubbing"; }
  };

  assert.equal(renderSubDubHelpers.updateSubDubLocalVolume(input), true);
  assert.equal(output.textContent, "42%");
});

test("SubDub exposes guarded Smart Multi speaker mapping and Voice Library controls", () => {
  const html = renderSubDub("/subdub?mode=subtitle_plus_dubbing");
  assert.match(html, /data-subdub-smart-multi/);
  assert.doesNotMatch(html, /name="speaker_mode"/);
  assert.doesNotMatch(html, /name="voice_profile_id"/);
  assert.match(html, /data-subdub-callback="videodub\|voice\|auto_speaker_gender"/);
  assert.match(html, /data-subdub-callback="videodub\|voice\|auto_multi_speaker"/);
  assert.match(html, /data-subdub-callback="videodub\|voice\|auto_smart_multivoice"/);
  assert.match(html, /Voice Library|Voice Vault|Thư viện giọng|Kho giọng/);
  assert.match(html, /name="target_language_custom"/);
  assert.match(html, /pattern="\[a-zA-Z\]\{2,5\}/);
  assert.match(html, /data-status="guarded"/);
  assert.equal((html.match(/data-subdub-voice-library-link/g) || []).length, 2);
  assert.equal((html.match(/href="\/voice\/saved\?return_to=%2Fsubdub%3Fmode%3Dsubtitle_plus_dubbing"/g) || []).length, 2);
});

test("SubDub exposes explicit default, saved, Auto 2, Auto Multi 3–8 and Smart Multi lanes", () => {
  const laneValues = [
    "default_female",
    "default_male",
    "saved_voice",
    "custom_voice",
    "auto_two",
    "auto_multi_3_8",
    "smart_multi"
  ];
  for (const locale of ["vi", "en", "zh"]) {
    const html = renderSubDub(`/subdub?lang=${locale}&mode=dubbing_only`, locale);
    for (const lane of laneValues) assert.match(html, new RegExp(`value="${lane}"`), `${locale} exposes ${lane}`);
    assert.match(html, /data-subdub-speaker-map/);
    assert.match(html, /data-subdub-callback="videodub\|voice\|auto_multi_speaker"/);
    assert.match(html, /data-subdub-callback="videodub\|voice\|auto_smart_multivoice"/);
  }
});

test("SubDub voice lanes keep one shared guard note instead of repeating it on every card", () => {
  const html = renderSubDub("/subdub?mode=subtitle_plus_dubbing");
  assert.doesNotMatch(html, /portal-subdub-voice-lane__body[^>]*>\s*<strong>[^<]+<\/strong>\s*<small>/);
  assert.match(html, /portal-subdub-voice-lane-note/);
});

test("SubDub keeps source subtitle state and the full localized language catalog explicit", () => {
  const viHtml = renderSubDub("/subdub?lang=vi&mode=subtitle_plus_dubbing", "vi");
  assert.match(viHtml, /name="subdub-subtitle-source-state"/);
  assert.match(viHtml, /value="with_subtitles"/);
  assert.match(viHtml, /value="without_subtitles" checked/);
  assert.match(viHtml, /id="subdub-source-file"[^>]*type="file"[^>]*disabled/);
  assert.match(viHtml, /<option value="auto" selected>Tự nhận diện<\/option>/);
  for (const code of ["vi", "en", "zh", "fr", "de", "es", "pt", "ru", "ar", "hi", "fil"]) {
    assert.match(viHtml, new RegExp(`<option value="${code}"`), `vi exposes ${code}`);
  }
  assert.match(viHtml, /<option value="vi" selected>Tiếng Việt<\/option>/);
  assert.equal((viHtml.match(/id="subdub-subtitle-position-/g) || []).length, 3);

  const enHtml = renderSubDub("/subdub?lang=en&mode=dubbing_only", "en");
  assert.match(enHtml, /<option value="vi" selected>Vietnamese<\/option>/);
  assert.doesNotMatch(enHtml, /Tiếng Việt|Tiếng Anh|Tiếng Trung/);

  const zhHtml = renderSubDub("/subdub?lang=zh&mode=dubbing_only", "zh");
  assert.match(zhHtml, /<option value="vi" selected>越南语<\/option>/);
  assert.doesNotMatch(zhHtml, /Tiếng Việt|Vietnamese/);
});

test("voice lane selection highlights the chosen lane and routes the library action", () => {
  const selectedLane = { classList: { toggles: [], toggle(name, enabled) { this.toggles.push([name, enabled]); } }, getAttribute(name) { return name === "data-subdub-voice-lane" ? "custom_voice" : ""; } };
  const savedLane = { classList: { toggles: [], toggle(name, enabled) { this.toggles.push([name, enabled]); } }, getAttribute(name) { return name === "data-subdub-voice-lane" ? "saved_voice" : ""; } };
  const libraryLink = { href: "", setAttribute(name, value) { if (name === "href") this.href = value; } };
  const lanes = {
    querySelectorAll() { return [selectedLane, savedLane]; },
    querySelector() { return libraryLink; }
  };
  const input = { value: "custom_voice", closest() { return lanes; } };

  assert.equal(renderSubDubHelpers.updateSubDubVoiceLaneSelection(input), true);
  assert.deepEqual(selectedLane.classList.toggles, [["is-selected", true]]);
  assert.deepEqual(savedLane.classList.toggles, [["is-selected", false]]);
  assert.equal(libraryLink.href, "/voice/clone");
});

test("SubDub subtitle layout exposes exactly seven canonical positions in each subtitle-capable mode", () => {
  const canonicalPositions = [
    "bottom_center",
    "bottom_left",
    "bottom_right",
    "top_center",
    "top_left",
    "top_right",
    "center"
  ];
  for (const mode of ["SUBTITLE_ONLY", "TRANSLATED_SUBTITLE", "SUBTITLE_PLUS_DUBBING"]) {
    const html = renderSubDub(`/subdub?mode=${mode.toLowerCase()}`);
    const panel = html.match(new RegExp(`data-subdub-mode-panel="${mode}"[\\s\\S]*?<\\/section>`))?.[0] || "";
    assert.match(panel, /class="portal-field portal-subdub-subtitle-position"/);
    for (const pos of canonicalPositions) {
      assert.match(panel, new RegExp(`<option value="${pos}"`), `${mode} exposes position ${pos}`);
    }
    assert.match(panel, /<option value="bottom_center" selected>/, `${mode} defaults to bottom_center`);
    assert.equal((panel.match(/<option value="(?:bottom_center|bottom_left|bottom_right|top_center|top_left|top_right|center)"/g) || []).length, 7);
  }
  const dubbingHtml = renderSubDub("/subdub?mode=dubbing_only");
  const dubbingPanel = dubbingHtml.match(/data-subdub-mode-panel="DUBBING_ONLY"[\s\S]*?<\/section>/)?.[0] || "";
  assert.doesNotMatch(dubbingPanel, /portal-subdub-subtitle-position/);
});

test("SubDub range output preserves zero and the local-setting note exists; mute confirmation is not covered", () => {
  const output = { textContent: "100%" };
  const panel = { querySelector(selector) { return selector.startsWith("[data-subdub-volume-output=") ? output : null; } };
  const inputOriginal = {
    value: "0",
    closest() { return panel; },
    getAttribute() { return "original"; }
  };
  const inputDubbing = {
    value: "0",
    closest() { return panel; },
    getAttribute() { return "dubbing"; }
  };

  assert.equal(renderSubDubHelpers.updateSubDubLocalVolume(inputOriginal), true);
  assert.equal(output.textContent, "0%", "zero volume is preserved for original audio");

  assert.equal(renderSubDubHelpers.updateSubDubLocalVolume(inputDubbing), true);
  assert.equal(output.textContent, "0%", "zero volume is preserved for dubbing audio");

  for (const locale of ["vi", "en", "zh"]) {
    const html = renderSubDub(`/subdub?lang=${locale}&mode=dubbing_only`, locale);
    assert.match(html, /portal-subdub-volume-note/);
    assert.match(html, /id="subdub-volume-note-dub"/);
  }
});

test("SubDub truthful guards prevent fake preview, speaker detection, quotes, or download ready state", () => {
  for (const mode of ["SUBTITLE_ONLY", "TRANSLATED_SUBTITLE", "DUBBING_ONLY", "SUBTITLE_PLUS_DUBBING"]) {
    const html = renderSubDub(`/subdub?mode=${mode.toLowerCase()}`);
    assert.doesNotMatch(html, /<video[^>]*src=/i, "no fake media preview video src");
    assert.doesNotMatch(html, /<audio[^>]*src=/i, "no fake media preview audio src");
    assert.doesNotMatch(html, /data-preview-url/i, "no fabricated preview url attribute");
    assert.doesNotMatch(html, /data-job-id="[^"]+"/i, "no fake job id attribute");
    assert.doesNotMatch(html, /data-provider-id/i, "no fabricated provider id attribute");
    assert.doesNotMatch(html, /data-subdub-download-ready/i, "no false download ready claim");
    assert.match(html, /id="subdub-source-file"[^>]*disabled/, "source upload is guarded");
    assert.match(html, /data-status="guarded"/, "stage 3 and stage 4 are marked guarded");
    assert.match(html, /data-subdub-report-empty/, "empty report is truthful");
  }
});

test("SubDub Stage 3 contains the selected-mode summary and keeps CTA guarded", () => {
  for (const [mode, query] of [
    ["SUBTITLE_ONLY", "subtitle_only"],
    ["TRANSLATED_SUBTITLE", "translated_subtitle"],
    ["DUBBING_ONLY", "dubbing_only"],
    ["SUBTITLE_PLUS_DUBBING", "subtitle_plus_dubbing"]
  ]) {
    const html = renderSubDub(`/subdub?mode=${query}`);
    assert.match(html, /data-subdub-stage="3"/);
    assert.match(html, /data-subdub-summary-mode/);
    assert.match(html, /class="portal-button portal-subdub-cta"[^>]*disabled[^>]*data-status="guarded"/);
    assert.doesNotMatch(html, /<form[^>]*action="\/api\/subdub/);
  }
});

test("SubDub markup matrix renders 24 mode-locale-theme combinations without execution controls or external src", () => {
  const locales = ["vi", "en", "zh"];
  const modes = ["subtitle_only", "translated_subtitle", "dubbing_only", "subtitle_plus_dubbing"];
  const themes = ["dark", "light"];
  let caseCount = 0;

  for (const locale of locales) {
    for (const mode of modes) {
      for (const theme of themes) {
        caseCount++;
        const html = renderSubDub(`/subdub?lang=${locale}&mode=${mode}&theme=${theme}`, locale);
        assert.ok(html.length > 500, `rendered output for ${locale}/${mode}/${theme}`);
        const foreignRequests = (html.match(/src="https?:\/\//gi) || []).length;
        assert.equal(foreignRequests, 0, `zero foreign requests in ${locale}/${mode}/${theme}`);
        assert.doesNotMatch(html, /data-portal-action="(?:feature-confirm|subdub-submit)"/);
        assert.match(html, /class="portal-page portal-subdub-hub/);
      }
    }
  }
  assert.equal(caseCount, 24, "exactly 24 matrix combinations evaluated");
});

test("SubDub links to existing companion hubs; return path and draft transfer are not covered", () => {
  const html = renderSubDub("/subdub");
  assert.match(html, /href="\/subtitle\/formats"/);
  assert.match(html, /href="\/subtitle\/assets"/);
  assert.match(html, /href="\/subtitle-studio"/);
  assert.match(html, /href="\/voice\/saved\?return_to=%2Fsubdub%3Fmode%3Dsubtitle_only"/);
});
