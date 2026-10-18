import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const portalSource = readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const catalogStart = portalSource.indexOf("  const SUBDUB_LANGUAGE_CATALOG = Object.freeze([");
const catalogEnd = portalSource.indexOf("  function renderSubDubLanguageOptions", catalogStart);
const workspaceStart = portalSource.indexOf("  const TRANSLATION_WORKSPACE_COPY = Object.freeze({");
const workspaceEnd = portalSource.indexOf("\n  function subtitleStudioCueFields", workspaceStart);

assert.notEqual(catalogStart, -1, "SubDub language catalog remains available for translation controls");
assert.notEqual(catalogEnd, -1, "SubDub language catalog boundary remains stable");
assert.notEqual(workspaceStart, -1, "Translation workspace copy is present");
assert.notEqual(workspaceEnd, -1, "Translation workspace helper boundary is present");

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#39;");
const renderTranslationWorkspace = new Function(
  "safeText",
  "badge",
  `${portalSource.slice(catalogStart, catalogEnd)}\n${portalSource.slice(workspaceStart, workspaceEnd)}\nreturn renderTranslationWorkspace;`
)(escapeHtml, (state) => `<span data-test-badge="${escapeHtml(state)}">${escapeHtml(state)}</span>`);

function render(locale, capabilities = {}) {
  return renderTranslationWorkspace(
    { routePath: "/subtitle-studio/new" },
    { locale, capabilities },
    { source_language: "auto", target_language: "en" }
  );
}

test("translation workspace keeps the complete source/target controls in one vertical flow", () => {
  const html = render("vi");
  assert.match(html, /data-translation-workspace/);
  assert.match(html, /data-translation-source-language/);
  assert.match(html, /value="auto" selected>Tự nhận diện/);
  assert.match(html, /data-translation-target-language/);
  assert.match(html, /data-translation-target-search/);
  assert.match(html, /data-translation-preserve-original checked/);
  assert.match(html, /data-translation-two-way/);
  assert.match(html, /data-translation-local-action="start"[^>]*disabled/);
  assert.match(html, /data-translation-local-action="stop"[^>]*disabled/);
  assert.match(html, /data-translation-result-state="empty"/);
  assert.match(html, /data-translation-history-state="empty"/);
  assert.doesNotMatch(html, /<form\b|data-portal-action=/, "the guarded panel cannot submit a new API payload");
  assert.equal((html.match(/<option[^>]+data-translation-target-option\b/g) || []).length, 21, "Bot language catalog remains visible");
});

test("translation workspace has clean locale copy for VI, EN and ZH", () => {
  const expected = {
    vi: ["Không gian dịch", "Ngôn ngữ nguồn", "Dịch hai chiều"],
    en: ["Translation workspace", "Source language", "Two-way translation"],
    zh: ["翻译工作区", "来源语言", "双向翻译"]
  };
  for (const [locale, labels] of Object.entries(expected)) {
    const html = render(locale);
    for (const label of labels) assert.match(html, new RegExp(label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")), `${locale} contains ${label}`);
    assert.match(html, /data-translation-state="guarded"/);
    assert.doesNotMatch(html, /provider|PayOS|wallet|Bot job/i, `${locale} does not leak technical execution jargon`);
  }
});

test("translation start controls only open from the server capability gate", () => {
  const html = render("en", { "translation-runtime-start": true });
  assert.match(html, /data-translation-state="ready"/);
  assert.doesNotMatch(html, /data-translation-local-action="start"[^>]*disabled/);
  assert.doesNotMatch(html, /data-translation-local-action="stop"[^>]*disabled/);
});

