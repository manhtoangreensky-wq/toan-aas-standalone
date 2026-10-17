import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const i18nSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal-i18n.js"), "utf8");
const portalSource = fs.readFileSync(path.join(repoRoot, "static/portal/portal.js"), "utf8");
const context = {};
vm.createContext(context);
vm.runInContext(i18nSource, context);
const messages = context.TOANAASI18n.messages;
const contentKeys = Object.keys(messages.vi).filter((key) => /^contentStudio\./.test(key));
const rendererStart = portalSource.indexOf("  // Creative Content Studio remains");
const rendererEnd = portalSource.indexOf("  function renderContentStudioDetail", rendererStart);
assert.notEqual(rendererStart, -1, "Content Studio source boundary exists");
assert.notEqual(rendererEnd, -1, "Content Studio board/new boundary exists");
const boardAuthoringSource = portalSource.slice(rendererStart, rendererEnd);

test("Content Studio keeps an equal, complete VI/EN/ZH catalogue", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).sort());
  assert.deepEqual(keysets[1], keysets[0], "VI and EN i18n keysets must remain equal");
  assert.deepEqual(keysets[2], keysets[0], "VI and ZH i18n keysets must remain equal");
  assert.ok(contentKeys.length >= 140, "Content Studio catalogue must cover board and new-brief chrome");
  for (const key of [
    "contentStudio.board.summary.title",
    "contentStudio.board.library.title",
    "contentStudio.board.filter.searchLabel",
    "contentStudio.kind.captionHashtag",
    "contentStudio.authoring.title",
    "contentStudio.authoring.form.submit",
    "contentStudio.field.titleLabel",
    "contentStudio.field.rightsNoteLabel",
    "contentStudio.pagination.next"
  ]) {
    assert.ok(messages.vi[key] && messages.en[key] && messages.zh[key], `missing locale copy: ${key}`);
  }
});
test("Content Studio board and new-brief chrome uses localized helpers without changing workflow contracts", () => {
  assert.match(portalSource, /function contentStudioText\(/);
  assert.match(boardAuthoringSource, /function contentStudioKindOptions\(/);
  assert.match(boardAuthoringSource, /function renderContentStudioPagination\(/);
  assert.match(boardAuthoringSource, /contentStudioText\("board\.summary\.title"/);
  assert.match(boardAuthoringSource, /contentStudioText\("authoring\.form\.submit"/);
  for (const staleFallback of [
    "Review boundary",
    "Authoring trước, execution sau",
    "Private authoring",
    "Owner-scoped library",
    "Audit-safe activity",
    "New private brief",
    "Content Operations Board",
    "Tạo Content Brief",
    "Tìm brief",
    "brief…"
  ]) {
    assert.ok(!boardAuthoringSource.includes(staleFallback), `legacy mixed-language fallback remains: ${staleFallback}`);
  }
  for (const contract of [
    'data-portal-action="content-brief-create"',
    'data-portal-action="content-studio-filter"',
    'data-portal-action="content-studio-refresh"',
    'data-portal-action="content-studio-page"',
    'href="/content-studio/new"',
    'href="/content-studio/${encodeURIComponent(id)}"'
  ]) {
    assert.ok(boardAuthoringSource.includes(contract), `Content Studio workflow contract missing: ${contract}`);
  }
});
