import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalPath = path.join(root, "static", "portal", "portal.js");
const i18nPath = path.join(root, "static", "portal", "portal-i18n.js");
const registryPath = path.join(root, "copyfast_registry.py");
const portalSource = fs.readFileSync(portalPath, "utf8");

function loadI18n() {
  const document = {
    title: "",
    documentElement: { lang: "", setAttribute() {} },
  };
  const window = {
    document,
    navigator: { language: "vi" },
    dispatchEvent() {},
    CustomEvent: function CustomEvent() {},
  };
  const context = vm.createContext({ window, document, Intl, Date, Number, String, Object, Array, Set, Map, Math, RegExp });
  vm.runInContext(fs.readFileSync(i18nPath, "utf8"), context, { filename: i18nPath });
  return window.TOANAASI18n;
}

const menuKeys = ["nav.workspaceMenu", "page.workspaceMenu.title", "page.workspaceMenu.description"];
const extraEntryKeys = [
  "featureCatalog.action.switchWorkspace",
  "featureCatalog.action.backDashboard",
];
const i18n = loadI18n();
const messages = i18n.messages;
for (const key of Object.keys(messages.vi)) {
  if (key.startsWith("workspaceMenu.")) menuKeys.push(key);
}
menuKeys.push(...extraEntryKeys);

const mixedVietnameseTerms = /\b(?:workspace|web|web-owned|web-native|memory center|tag|pause|resume|complete|account|planning|record|brief|calendar marker|self-review|campaign planner|content|chat|context|prompt studio|image studio|art direction|reference|image prompt composer|direction|document workspace|ownership|capability|transcript|cue|asset vault|audio library|audio brief|music|metadata|provider|signed session|canonical|authority|tier|catalog(?:ue)?|directory|workflow|purchase|checkout|rate|owner-scoped|support desk|navigation only|reviewed|portal|route|callback|message|pending|phase|state|credit|permission|server-verified|workspace menu|switch workspace|dashboard)\b/i;
const approvedChineseLatin = new Set(["TOAN", "AAS", "BOT", "TELEGRAM", "ID", "CSRF", "PDF", "XU", "URL", "API"]);

function visibleStrings(source) {
  return [...source.matchAll(/\b(?:eyebrow|title|description):\s*"([^"]*)"/g)].map((match) => match[1]);
}

function workspaceCatalogFallbacks(source) {
  const start = source.indexOf("const WORKSPACE_MENU_CAPABILITY_SPECS = Object.freeze([");
  const end = source.indexOf("function normalizeWorkspaceMenuCapabilities", start);
  assert.ok(start >= 0 && end > start, "workspace menu catalog must remain present");
  return visibleStrings(source.slice(start, end));
}

function workspaceTextFallbacks(source) {
  const start = source.indexOf("function workspaceMenuEntryState(");
  const end = source.indexOf("function validWorkspaceDraftId", start);
  assert.ok(start >= 0 && end > start, "workspace menu renderer must remain present");
  const renderer = source.slice(start, end);
  return [...renderer.matchAll(/workspaceMenuText\(\s*"[^"]+"\s*,\s*"((?:[^"\\]|\\.)*)"/g)].map((match) => match[1]);
}

test("workspace-menu and its entry points keep complete locale key coverage", () => {
  const expected = [...new Set(menuKeys)].sort();
  assert.equal(expected.filter((key) => key.startsWith("workspaceMenu.")).length, 70);
  for (const locale of ["vi", "en", "zh"]) {
    const actual = Object.keys(messages[locale])
      .filter((key) => key.startsWith("workspaceMenu.") || key === "nav.workspaceMenu" || key.startsWith("page.workspaceMenu.") || extraEntryKeys.includes(key))
      .sort();
    assert.deepEqual(actual, expected, `${locale} must translate every workspace-menu string`);
    for (const key of expected) assert.ok(messages[locale][key]?.trim(), `${locale}.${key} must not be empty`);
  }
});

test("Vietnamese workspace-menu copy and source fallbacks contain no mixed English UI jargon", () => {
  const values = menuKeys.map((key) => [key, messages.vi[key]]);
  for (const value of workspaceCatalogFallbacks(portalSource)) values.push(["portal.js catalog fallback", value]);
  for (const value of workspaceTextFallbacks(portalSource)) values.push(["portal.js render fallback", value]);
  for (const [key, value] of values) assert.doesNotMatch(value, mixedVietnameseTerms, `vi.${key}: ${value}`);
});

test("English workspace-menu copy does not fall back to Vietnamese text", () => {
  for (const key of menuKeys) {
    assert.doesNotMatch(messages.en[key], /[\u00C0-\u024F]/u, `en.${key}: ${messages.en[key]}`);
  }
});

test("Chinese workspace-menu copy translates generic English UI words", () => {
  for (const key of menuKeys) {
    const withoutTemplateTokens = messages.zh[key].replace(/\{[^}]+\}/g, "");
    const latinWords = withoutTemplateTokens.match(/[A-Za-z][A-Za-z0-9]*/g) || [];
    const unexpected = latinWords.filter((word) => !approvedChineseLatin.has(word.toUpperCase()));
    assert.deepEqual(unexpected, [], `zh.${key} contains untranslated words: ${unexpected.join(", ")}`);
  }
});

test("the workspace-menu card in the feature catalogue follows the selected locale", () => {
  const start = portalSource.indexOf("function moduleCard(");
  const end = portalSource.indexOf("\n  function fallbackCatalogGroup", start);
  assert.ok(start >= 0 && end > start, "module card renderer must remain present");
  const moduleCardSource = portalSource.slice(start, end);

  for (const locale of ["vi", "en", "zh"]) {
    i18n.setLocale(locale, { emit: false });
    const sandbox = vm.createContext({
      uiText: (key, fallback, params) => i18n.t(key, params) || fallback,
      featureCatalogText: (key, fallback, params) => i18n.t(`featureCatalog.${key}`, params) || fallback,
      safeCatalogRoute: (route) => route,
      normalizePath: (route) => route,
      manifest: { "/workspace-menu": { path: "/workspace-menu", access: "member", icon: "menu" } },
      ALLOWED_STATES: new Set(["ready", "guarded", "read_only"]),
      catalogEntryState: () => "read_only",
      renderEngineLabel: () => "",
      renderReadinessLabel: () => "",
      portalIcon: () => "",
      safeText: (value) => String(value ?? ""),
      badge: (state) => `<span>${state}</span>`,
      ICONS: { default: "menu" },
    });
    vm.runInContext(`${moduleCardSource}; globalThis.renderModuleCard = moduleCard;`, sandbox);
    const html = sandbox.renderModuleCard({
      key: "workspace_menu",
      route: "/workspace-menu",
      title: "Không gian làm việc",
      description: "Danh sách lối vào theo mục tiêu công việc.",
      availability: "available",
    }, {}, "Mở", { showEngineLabel: true });
    assert.ok(html.includes(messages[locale]["page.workspaceMenu.title"]), `${locale} card title must be localized`);
    assert.ok(html.includes(messages[locale]["page.workspaceMenu.description"]), `${locale} card description must be localized`);
  }
});

test("workspace-menu route and fallback labels stay Vietnamese without changing its route", () => {
  assert.ok(/customerPage\("\/workspace-menu", "Không gian làm việc"/.test(portalSource), "route title fallback must be Vietnamese");
  assert.ok(/"Không gian làm việc": "nav\.workspaceMenu"/.test(portalSource), "navigation label lookup must use the localized label");
  assert.ok(/featureCatalogText\("action\.switchWorkspace", "Mở danh sách không gian"\)/.test(portalSource), "catalog entry point must have a Vietnamese fallback");
  assert.ok(/featureCatalogText\("action\.backDashboard", "Về trang tổng quan"\)/.test(portalSource), "dashboard entry point must have a Vietnamese fallback");
  const registry = fs.readFileSync(registryPath, "utf8");
  const registration = registry.match(/WebFeature\("workspace_menu",\s*"([^"]+)",\s*"[^"]+",\s*"[^"]+",\s*description="([^"]*)"\)/);
  assert.ok(registration, "workspace menu registry entry must keep its reviewed key and route");
  assert.equal(registration[1], "Không gian làm việc", "registered display label must be Vietnamese");
  assert.doesNotMatch(`${registration[1]} ${registration[2]}`, mixedVietnameseTerms, "registered Vietnamese display copy must not mix English UI jargon");
});
