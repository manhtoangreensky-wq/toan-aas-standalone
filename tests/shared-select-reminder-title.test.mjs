import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import {fileURLToPath} from "node:url";
import {execFileSync} from "node:child_process";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
let helper = fs.readFileSync(path.join(ROOT, "tests/helpers/shared-select-labels-runtime.mjs"), "utf8");
const changes = [
  ['export const DEFAULT_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");',
    "export const DEFAULT_ROOT = " + JSON.stringify(ROOT) + ";"],
  ['Object.freeze({renderFields});', 'Object.freeze({renderFields,localizedPageTitle,documentTitle});'],
  ["    source, messages: i18n.messages,", `    source, messages: i18n.messages,
    renderTitle(page, context) {
      const before = JSON.stringify([page, context]);
      const result = {page: renderWindow.__sharedSelectQA.localizedPageTitle(page, context),
        document: renderWindow.__sharedSelectQA.documentTitle(page, context)};
      assert.equal(JSON.stringify([page, context]), before);
      assert.deepEqual(attempts, []);
      return result;
    },`]
];
for (const [old, next] of changes) {
  assert.equal(helper.split(old).length - 1, 1, "Exact test-local title exposure");
  helper = helper.replace(old, () => next);
}
const {runtime, sources, freeze} = await import("data:text/javascript;base64," + Buffer.from(helper).toString("base64"));
const actual = sources();
const baseline = {
  ...actual,
  raw: Object.fromEntries(Object.entries({portal: "static/portal/portal.js", i18n: "static/portal/portal-i18n.js"})
    .map(([key, file]) => [key, execFileSync("git", ["show", "46423a6df9af67ac7ccabd88686d4cb42523a078:" + file],
      {cwd: ROOT, encoding: "utf8", maxBuffer: 12e6})]))
};
const labels = {vi: "Nhắc việc", en: "Reminders", zh: "提醒"};
const page = freeze({path: "/reminders", routePath: "/reminders", title: "Nhắc việc", layout: "memory-reminders", access: "member"});
for (const locale of ["vi", "en", "zh"]) {
  test(locale + ": reminders uses its existing route label for real generic server title and stale language title", () => {
    const instance = runtime(actual, locale);
    for (const title of ["TOAN AAS Workspace", "TOAN AAS 工作台", "Nhắc việc", "FIXED SERVER ROUTE TITLE"]) {
      const result = instance.renderTitle(page, freeze({title}));
      assert.deepEqual(JSON.parse(JSON.stringify(result)), {page: labels[locale], document: labels[locale] + " · TOAN AAS"});
    }
  });
  test(locale + ": sibling routes and explicit custom server titles retain exact BASE resolution", () => {
    const now = runtime(actual, locale), before = runtime(baseline, locale);
    for (const route of ["/notes", "/projects", "/account/security", "/media-workspace/new", "/customer-unmapped"]) {
      const sibling = freeze({path: route, routePath: route, title: "SIBLING CUSTOMER TITLE", layout: "none", access: "member"});
      for (const title of ["TOAN AAS Workspace", "TOAN AAS 工作台", "Facebook TikTok media studio", "<img src=x>&"]) {
        const context = freeze({title});
        assert.deepEqual(JSON.parse(JSON.stringify(now.renderTitle(sibling, context))),
          JSON.parse(JSON.stringify(before.renderTitle(sibling, context))));
      }
    }
  });
}
test("same VM locale changes immediately recompute reminder page and tab titles", () => {
  const instance = runtime(actual, "vi"), context = freeze({title: "TOAN AAS 工作台"});
  for (const locale of ["vi", "en", "zh", "vi"]) {
    instance.setLocale(locale);
    const result = instance.renderTitle(page, context);
    assert.equal(result.page, labels[locale]);
    assert.equal(result.document, labels[locale] + " · TOAN AAS");
  }
});
