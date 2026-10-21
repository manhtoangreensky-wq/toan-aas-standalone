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
const sourceStart = portalSource.indexOf("  function contentPromptPackFields()");
const sourceEnd = portalSource.indexOf("  function publishReviewPackFields()", sourceStart);
assert.notEqual(sourceStart, -1, "Content Prompt Pack renderer boundary exists");
assert.notEqual(sourceEnd, -1, "Content Prompt Pack renderer ends before Publish Review");
const source = portalSource.slice(sourceStart, sourceEnd);

test("Content Prompt Pack fixed chrome has equal VI/EN/ZH coverage", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).filter((key) => key.startsWith("contentPromptPack.")).sort());
  assert.deepEqual(keysets[1], keysets[0], "Content Prompt Pack VI and EN keysets must remain equal");
  assert.deepEqual(keysets[2], keysets[0], "Content Prompt Pack VI and ZH keysets must remain equal");
  assert.ok(keysets[0].length >= 50, "Content Prompt Pack catalogue must cover form, suggestions, result, receipt and boundary chrome");
});

test("Vietnamese Content Prompt Pack chrome does not leak generic English", () => {
  const leaked = /\b(?:Editable|deterministic|draft|result|composer|Execution|boundary|Provider|call|Job|payment|asset|publish|browser|owner-only|pending|engine|Topic|Server|Content|Pack|Prompt|review|approval|Web-native)\b/i;
  const leaks = Object.entries(messages.vi)
    .filter(([key]) => key.startsWith("contentPromptPack."))
    .filter(([, value]) => leaked.test(String(value)));
  assert.deepEqual(leaks, [], `unexpected generic English in VI Content Prompt Pack copy: ${JSON.stringify(leaks)}`);
});

test("Content Prompt Pack renderer routes fixed chrome through the locale helper", () => {
  for (const helperCall of [
    'contentPromptPackText("field.kindLabel"',
    'contentPromptPackText("suggestions.title"',
    'contentPromptPackText("result.kicker"',
    'contentPromptPackText("receipt.title"',
    'contentPromptPackText("intro.title"',
    'contentPromptPackText("boundary.title"',
    'contentPromptPackText("scope.title"'
  ]) {
    assert.ok(source.includes(helperCall), `missing localized helper call: ${helperCall}`);
  }
  for (const staleFixedCopy of [
    "Local deterministic draft",
    "Editable draft result",
    "Draft composer",
    "Execution boundary",
    "Provider call",
    "Job / payment",
    "Editable text draft",
    "owner-only"
  ]) {
    assert.ok(!source.includes(staleFixedCopy), `mixed-language Content Prompt Pack copy remains: ${staleFixedCopy}`);
  }
  for (const contract of [
    'data-portal-action="content-prompt-pack-compose"',
    'data-portal-action="content-prompt-pack-save-memory"',
    'data-content-prompt-suggestion=',
    'data-content-prompt-suggestion-kind='
  ]) {
    assert.ok(source.includes(contract), `Content Prompt Pack workflow contract missing: ${contract}`);
  }
});
