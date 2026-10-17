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
const start = portalSource.indexOf("  function publishReviewPackFields");
const end = portalSource.indexOf("  // Contextual Ad Prompt", start);
assert.notEqual(start, -1, "Publish Review source boundary exists");
assert.notEqual(end, -1, "Publish Review ends before the next feature");
const source = portalSource.slice(start, end);
const publishKeys = Object.keys(messages.vi).filter((key) => /^publishReview\./.test(key));

test("Publish Review has equal VI/EN/ZH fixed chrome", () => {
  const keysets = ["vi", "en", "zh"].map((locale) => Object.keys(messages[locale]).sort());
  assert.deepEqual(keysets[1], keysets[0], "VI and EN i18n keysets must remain equal");
  assert.deepEqual(keysets[2], keysets[0], "VI and ZH i18n keysets must remain equal");
  assert.ok(publishKeys.length >= 50, "Publish Review catalogue must cover page, form, result, boundary and scope chrome");
  for (const key of [
    "publishReview.page.title",
    "publishReview.field.captionLabel",
    "publishReview.field.sourcePromptHelp",
    "publishReview.result.checklistTitle",
    "publishReview.composer.submit",
    "publishReview.boundary.title",
    "publishReview.scope.body",
    "publishReview.notes.safetyBody"
  ]) {
    assert.ok(messages.vi[key] && messages.en[key] && messages.zh[key], `missing Publish Review locale copy: ${key}`);
  }
});
test("Publish Review localizes fixed controls without changing the workflow boundary", () => {
  for (const helperCall of [
    'publishReviewText("field.titleLabel"',
    'publishReviewText("field.captionLabel"',
    'publishReviewText("result.checklistTitle"',
    'publishReviewText("composer.title"',
    'publishReviewText("boundary.title"',
    'publishReviewText("scope.title"'
  ]) {
    assert.ok(source.includes(helperCall), `Publish Review must use localized helper: ${helperCall}`);
  }
  for (const staleFixedCopy of [
    "Web-native review only",
    "Review receipt",
    "Review composer",
    "Execution boundary",
    "Social connections",
    "Publish actions",
    "Reviewable text pack",
    "Hashtag & CTA",
    "Prompt nền để đối chiếu",
    "Checklist trước khi dùng bên ngoài",
    "Scope rõ ràng",
    "review package",
    "Social / scheduler",
    "Bot / provider",
    "Job / wallet / PayOS",
    "Asset / publish"
  ]) {
    assert.ok(!source.includes(staleFixedCopy), `mixed-language Publish Review copy remains: ${staleFixedCopy}`);
  }
  for (const contract of [
    'data-portal-action="publish-review-pack-compose"',
    'data-portal-route="/content/publish-review"',
    'href="/content-studio"',
    'href="/workboard"',
    "normalizePublishReviewPackResult",
    "publishReviewPackList"
  ]) {
    assert.ok(source.includes(contract), `Publish Review workflow contract missing: ${contract}`);
  }
});
