import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const source = fs.readFileSync("static/portal/portal.js", "utf8");
const messages = fs.readFileSync("static/portal/portal-i18n.js", "utf8");
const shell = fs.readFileSync("copyfast_pages.py", "utf8");
const untranslated = /\b(?:media|studio|workspace|web|brief|workflow|registry|route|project|job|browser|storyboard|CTA|input|estimate|guarded|assets|canonical|output|delivery|video|content|visual|voice|music|finalization|review)\b/i;
const visibleText = (html) => html.replace(/<svg\b[\s\S]*?<\/svg>/g, " ").replace(/<[^>]*>/g, " ").replace(/&(?:amp|quot|lt|gt|#39);/g, " ").replace(/\s+/g, " ").trim();

function runtime(locale) {
  const noop = () => {};
  const document = { readyState: "loading", title: "", addEventListener: noop, querySelector: () => null, querySelectorAll: () => [], getElementById: () => null,
    documentElement: { lang: locale, setAttribute: noop, getAttribute: () => null, classList: { add: noop, remove: noop } },
    body: { classList: { add: noop, remove: noop, toggle: noop }, setAttribute: noop } };
  const window = { document, navigator: { language: locale, userAgent: "Locale QA" }, location: { pathname: "/studio", search: "", href: "https://unit.invalid/studio" },
    addEventListener: noop, dispatchEvent: noop, CustomEvent: function () {}, matchMedia: () => ({ matches: false, addEventListener: noop }),
    localStorage: { getItem: () => null, setItem: () => { throw Error("No browser storage writes"); } } };
  const sandbox = vm.createContext({ window, document, navigator: window.navigator, URL, URLSearchParams, Intl, console, setTimeout: noop, clearTimeout: noop,
    fetch: () => { throw Error("No network in locale tests"); } });
  vm.runInContext(messages, sandbox);
  const marker = "  window.TOANAASPortal = Object.freeze({";
  assert.ok(source.includes(marker));
  vm.runInContext(source.replace(marker, "  window.__StudioLocaleTest = {normalizeBootstrap,renderMediaStudio,renderHeader,localizedNavigationLabel,localizedPageTitle,documentTitle};\n" + marker), sandbox);
  window.TOANAASI18n.setLocale(locale, { emit: false });
  const raw = { path: "/studio", profile: { locale, displayName: "QA" }, session: { authenticated: true, csrfToken: "synthetic-locale-test", displayName: "QA" }, capabilities: {} };
  window.__TOAN_AAS_PORTAL__ = raw;
  const api = window.__StudioLocaleTest;
  return { window, api, page: window.TOANAASPortal.resolvePage("/studio"), context: api.normalizeBootstrap(raw) };
}

test("Vietnamese /studio renders a translated title, introduction and six workflow cards", () => {
  const r = runtime("vi");
  const html = r.api.renderMediaStudio(r.page, r.context);
  const text = visibleText(html);
  assert.ok(text.includes("Xưởng sáng tạo"));
  assert.ok(text.includes("Một quy trình rõ ràng cho dự án sáng tạo"));
  assert.ok(text.includes("Lập bản định hướng"));
  assert.ok(text.includes("Mở bảng phân cảnh"));
  assert.ok(text.includes("Mở trung tâm tác vụ"));
  assert.doesNotMatch(text, untranslated);
  assert.equal((html.match(/class="portal-media-studio-step"/g) || []).length, 6);
  assert.deepEqual(Array.from(html.matchAll(/class="portal-button[^\"]*" href="([^\"]+)"/g), (match) => match[1]),
    ["/features", "/content/storyboard", "/video/product", "/approvals", "/jobs", "/assets", "/jobs", "/assets", "/features"]);
  assert.doesNotMatch(html, /<form\b|data-portal-action=/);
});

test("Vietnamese navigation, page heading and document title share the translated name", () => {
  const r = runtime("vi");
  assert.equal(r.api.localizedPageTitle(r.page, r.context), "Xưởng sáng tạo");
  assert.equal(r.api.localizedNavigationLabel("Media Studio"), "Xưởng sáng tạo");
  assert.equal(r.api.documentTitle(r.page, r.context), "Xưởng sáng tạo · TOAN AAS");
  assert.doesNotMatch(visibleText(r.api.renderHeader(r.page, r.context)), /Media Studio/i);
});

test("all fixed Vietnamese Media Studio labels are translated", () => {
  const r = runtime("vi");
  const entries = Object.entries(r.window.TOANAASI18n.messages.vi).filter(([key]) => key.startsWith("mediaStudio."));
  assert.equal(entries.length, 41);
  for (const [key, value] of entries) {
    assert.ok(value.trim(), `${key} is not empty`);
    assert.doesNotMatch(value, untranslated, `${key} contains untranslated fixed copy`);
  }
});

test("first-paint server title uses Vietnamese while English and Chinese titles stay unchanged", () => {
  const title = shell.match(/^\s*"\/studio": \{([^\n]+)\},?$/m);
  assert.ok(title, "the /studio first-paint page title is present");
  assert.match(title[1], /"vi": "Xưởng sáng tạo · TOAN AAS"/);
  assert.match(title[1], /"en": "Media Studio · TOAN AAS"/);
  assert.match(title[1], /"zh": "媒体工作室 · TOAN AAS"/);
});

test("SubDub navigation and fixed labels are Vietnamese-only without changing English or Chinese", () => {
  const vi = runtime("vi");
  const viMessages = vi.window.TOANAASI18n.messages.vi;
  assert.equal(vi.api.localizedNavigationLabel("SubDub"), "Phụ đề & Lồng tiếng");
  assert.equal(vi.api.localizedNavigationLabel("AI SubDub"), "Phụ đề & Lồng tiếng");
  for (const [key, value] of [
    ["customerChrome.nav.subdub", "Phụ đề & Lồng tiếng"],
    ["assistant.action.subdub", "Phụ đề & Lồng tiếng"],
    ["voiceUi.workspace.returnSubDub", "Quay lại Phụ đề & Lồng tiếng"],
    ["voiceUi.library.openSubDub", "Mở Phụ đề & Lồng tiếng"],
    ["dashboard.productHero.subdub.title", "Phụ đề & Lồng tiếng"],
    ["dashboard.productHero.subdub.open", "Mở Phụ đề & Lồng tiếng"]
  ]) assert.equal(viMessages[key], value, `${key} is translated`);
  for (const locale of ["en", "zh"]) {
    const r = runtime(locale);
    const copy = r.window.TOANAASI18n.messages[locale];
    assert.equal(r.api.localizedNavigationLabel("SubDub"), "SubDub");
    assert.equal(r.api.localizedNavigationLabel("AI SubDub"), "AI SubDub");
    for (const [key, values] of Object.entries({
      "customerChrome.nav.subdub": ["SubDub", "SubDub"],
      "assistant.action.subdub": ["SubDub", "SubDub"],
      "voiceUi.workspace.returnSubDub": ["Back to SubDub", "返回 SubDub"],
      "voiceUi.library.openSubDub": ["Open SubDub", "打开 SubDub"],
      "dashboard.productHero.subdub.title": ["SubDub", "SubDub"],
      "dashboard.productHero.subdub.open": ["Open SubDub", "打开 SubDub"]
    })) assert.equal(copy[key], values[locale === "en" ? 0 : 1], `${locale}.${key} stays unchanged`);
  }
});

for (const [locale, title, intro] of [["en", "Media Studio", "One clear flow for a media project"], ["zh", "媒体工作室", "一条清晰的媒体项目流程"]]) {
  test(`${locale}: Media Studio keeps its own language and routes`, () => {
    const r = runtime(locale);
    const html = r.api.renderMediaStudio(r.page, r.context);
    assert.equal(r.api.localizedPageTitle(r.page, r.context), title);
    assert.ok(html.includes(intro));
    assert.doesNotMatch(html, /Xưởng sáng tạo|Lập bản định hướng/);
    assert.equal((html.match(/class="portal-media-studio-step"/g) || []).length, 6);
    assert.match(html, /href="\/video\/product"/);
  });
}
