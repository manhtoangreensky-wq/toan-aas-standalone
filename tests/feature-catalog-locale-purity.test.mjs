import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const i18nPath = path.join(root, "static", "portal", "portal-i18n.js");
const portalPath = path.join(root, "static", "portal", "portal.js");
const i18nSource = fs.readFileSync(i18nPath, "utf8");
const portalSource = fs.readFileSync(portalPath, "utf8");

function loadMessages() {
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
  vm.runInContext(i18nSource, context, { filename: i18nPath });
  return window.TOANAASI18n.messages;
}

const messages = loadMessages();
const catalogKeys = Object.keys(messages.vi).filter((key) => key.startsWith("featureCatalog.")).sort();
const mixedVietnameseTerms = /\b(?:workflow|web|web-native|workspace|content|chat|prompt|caption|script|planning|canonical|core bridge|portal|catalogue|catalog|route|dashboard|metadata|delivery|ticket|provider|worker|backup|callback|execution|output|signed session|capability|readiness|engine|payment|brief|preview|export|voice studio|voice vault|clone|music|sfx|documents|image studio|studio|asset|library|reference|directory|registry|customer|system state|map route|audit|guarded|compatibility|job|tag|web app|account)\b/i;
const approvedChineseLatin = new Set(["TOAN", "AAS", "BOT", "TELEGRAM", "PAYOS", "ID", "CSRF", "PDF", "XU", "URL", "API", "SFX", "TTS", "ASR", "SRT", "VTT", "OCR", "USD", "VND", "QR", "AI", "MP3", "M4A"]);

function featureCatalogFallbacks(source) {
  const start = source.indexOf("const FEATURE_CATALOG_GROUPS = Object.freeze([");
  const end = source.indexOf("function featureCatalogGroupCopy", start);
  assert.ok(start >= 0 && end > start, "feature catalog groups must remain present");
  const groups = source.slice(start, end);
  const groupCopy = [...groups.matchAll(/\b(?:title|description):\s*"([^"]*)"/g)].map((match) => match[1]);
  const directFallbacks = [...source.matchAll(/featureCatalogText\(\s*(?:"[^"]+"|`[^`]+`)\s*,\s*"([^"]*)"/g)].map((match) => match[1]);
  return [...groupCopy, ...directFallbacks];
}

test("feature-catalog messages have matching, nonempty coverage in vi/en/zh", () => {
  assert.equal(catalogKeys.length, 296);
  for (const locale of ["vi", "en", "zh"]) {
    const localeKeys = Object.keys(messages[locale]).filter((key) => key.startsWith("featureCatalog.")).sort();
    assert.deepEqual(localeKeys, catalogKeys, `${locale} must define every feature-catalog string`);
    for (const key of catalogKeys) assert.ok(messages[locale][key]?.trim(), `${locale}.${key} must not be empty`);
  }
});

test("each static feature-catalog key is declared once per supported locale", () => {
  const counts = new Map();
  for (const [, key] of i18nSource.matchAll(/"(featureCatalog\.[^"]+)"\s*:/g)) {
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  assert.equal(counts.size, catalogKeys.length);
  for (const key of catalogKeys) assert.equal(counts.get(key), 3, `${key} must be declared exactly once in vi/en/zh`);
});

test("Vietnamese feature-catalog copy and source fallbacks avoid mixed English interface terms", () => {
  const values = catalogKeys.map((key) => [key, messages.vi[key]]);
  for (const value of featureCatalogFallbacks(portalSource)) values.push(["portal.js feature-catalog fallback", value]);
  const failures = values.filter(([, value]) => mixedVietnameseTerms.test(value)).map(([key, value]) => `vi.${key}: ${value}`);
  assert.deepEqual(failures, [], failures.join("; "));
});

test("English feature-catalog copy contains no Vietnamese text", () => {
  for (const key of catalogKeys) {
    assert.doesNotMatch(messages.en[key], /[\u00C0-\u024F]/u, `en.${key}: ${messages.en[key]}`);
  }
});

test("Chinese feature-catalog copy translates generic English interface terms", () => {
  const failures = [];
  for (const key of catalogKeys) {
    const withoutTemplateTokens = messages.zh[key].replace(/\{[^}]+\}/g, "");
    const latinWords = withoutTemplateTokens.match(/[A-Za-z][A-Za-z0-9]*/g) || [];
    const unexpected = latinWords.filter((word) => !approvedChineseLatin.has(word.toUpperCase()));
    if (unexpected.length) failures.push(`zh.${key}: ${unexpected.join(", ")}`);
  }
  assert.deepEqual(failures, [], failures.join("; "));
});
