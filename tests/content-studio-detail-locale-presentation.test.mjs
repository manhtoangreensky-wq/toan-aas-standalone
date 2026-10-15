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
const detailStart = portalSource.indexOf("  function contentVariantFields");
const detailEnd = portalSource.indexOf("  // Channel Strategy", detailStart);
assert.notEqual(detailStart, -1, "Content Studio detail helpers source boundary exists");
assert.notEqual(detailEnd, -1, "Content Studio detail ends before the next feature");
const detailSource = portalSource.slice(detailStart, detailEnd);

test("Content Studio detail keeps an equal VI/EN/ZH catalogue", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).sort());
  assert.deepEqual(keysets[1], keysets[0], "VI and EN i18n keysets must remain equal");
  assert.deepEqual(keysets[2], keysets[0], "VI and ZH i18n keysets must remain equal");
  for (const key of [
    "contentStudio.detail.pageTitle",
    "contentStudio.detail.notFoundTitle",
    "contentStudio.detail.editor.archiveConfirm",
    "contentStudio.detail.composer.title",
    "contentStudio.detail.manual.title",
    "contentStudio.detail.variants.kindLabel",
    "contentStudio.detail.variants.restoreVersionConfirm",
    "contentStudio.detail.history.restoreConfirm",
    "contentStudio.detail.activity.empty"
  ]) {
    assert.ok(messages.vi[key] && messages.en[key] && messages.zh[key], `missing detail locale copy: ${key}`);
  }
});
test("Content Studio detail localizes fixed controls without changing workflow contracts", () => {
  for (const helperCall of [
    'contentStudioText("detail.editor.title"',
    'contentStudioText("detail.composer.title"',
    'contentStudioText("detail.manual.title"',
    'contentStudioText("detail.variants.kindLabel"',
    'contentStudioText("detail.history.title"',
    'contentStudioText("detail.activity.body"'
  ]) {
    assert.ok(detailSource.includes(helperCall), `detail must use localized helper: ${helperCall}`);
  }
  for (const staleFixedCopy of [
    "Archive content piece",
    "Lịch sử content piece",
    "Content piece",
    "Archive brief",
    "Brief & review context",
    "Local deterministic drafts",
    "Manual authoring",
    "Content pieces",
    "owner check",
    "optimistic revision",
    "audit feed"
  ]) {
    assert.ok(!detailSource.includes(staleFixedCopy), `mixed-language detail copy remains: ${staleFixedCopy}`);
  }
  for (const contract of [
    'data-portal-action="content-brief-update"',
    'data-portal-action="content-variant-create"',
    'data-portal-action="content-variant-update"',
    'data-portal-action="content-variant-restore-version"',
    'data-content-brief-id=',
    'data-content-variant-id=',
    'data-content-variant-revision=',
    'data-content-variant-version='
  ]) {
    assert.ok(detailSource.includes(contract), `detail workflow contract missing: ${contract}`);
  }
});
