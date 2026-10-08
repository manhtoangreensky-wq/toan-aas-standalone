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
const rendererSource = portalSource.slice(rendererStart, rendererEnd);
const renderSubDubHelpers = new Function(`${helperSource}\nreturn { updateSubDubModeSelection, updateSubDubLocalVolume };`)();
const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#39;");

function renderSubDub(url, locale = "vi", wallet = { balance_xu: 246 }) {
  const parsed = new URL(url, "https://app.example");
  const browserWindow = { location: { search: parsed.search } };
  const render = new Function(
    "window",
    "interfaceLocaleFor",
    "safeText",
    "badge",
    "renderHero",
    `${helperSource}\n${rendererSource}\nreturn { renderSubDubHub, updateSubDubModeSelection, updateSubDubLocalVolume };`
  )(
    browserWindow,
    (context) => context?.locale || locale,
    escapeHtml,
    (state) => `<span data-test-badge="${escapeHtml(state)}">${escapeHtml(state)}</span>`,
    (page) => `<header class="test-route-hero"><h1>${escapeHtml(page?.title || "SubDub")}</h1><p>${escapeHtml(page?.description || "")}</p></header>`
  );

  return render.renderSubDubHub({ title: "SubDub" }, { locale, wallet });
}

test("SubDub mode selection stays on one screen and exposes all four choices", () => {
  const html = renderSubDub("/subdub?mode=dubbing_only");

  assert.equal((html.match(/data-subdub-mode-select=/g) || []).length, 4);
  assert.equal((html.match(/data-subdub-mode-panel=/g) || []).length, 4);
  assert.match(html, /data-subdub-mode-select="DUBBING_ONLY"[^>]*aria-pressed="true"/);
  assert.match(html, /data-subdub-mode-panel="SUBTITLE_ONLY"[^>]*hidden/);
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
  const panels = buttons.map((button) => ({ mode: button.key, hidden: true, getAttribute() { return this.mode; } }));
  const summary = { textContent: "" };
  const page = {
    querySelectorAll(selector) { return selector === "[data-subdub-mode-select]" ? buttons : panels; },
    querySelector() { return summary; }
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
  const finalUrl = new URL(replacedUrl);
  assert.equal(finalUrl.pathname, "/subdub");
  assert.equal(finalUrl.searchParams.get("lang"), "vi");
  assert.equal(finalUrl.searchParams.get("mode"), "subtitle_plus_dubbing");
  assert.equal(finalUrl.hash, "#hub");
});

test("local volume input updates its visible value only", () => {
  const output = { textContent: "100%" };
  const panel = { querySelector() { return output; } };
  const input = {
    value: "42",
    closest() { return panel; },
    getAttribute() { return "dubbing"; }
  };

  assert.equal(renderSubDubHelpers.updateSubDubLocalVolume(input), true);
  assert.equal(output.textContent, "42%");
});
