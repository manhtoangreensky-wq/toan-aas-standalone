import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {execFileSync} from "node:child_process";
import {requiredWarningHistoricalSource as inverse, requiredWarningHistoricalSnapshot as snapshot}
  from "./helpers/portal-required-warning-historical.mjs";
import {imageStudioFieldsHistoricalSource} from "./helpers/image-studio-fields-historical.mjs";

const base = "a09c7cc94a82537f77ab4e016d3dfa9ae7f23fcc";
const lf = value => value.replace(/\r\n/g, "\n");
const oldToast = 'showToast("Hãy hoàn tất các trường bắt buộc trước khi tiếp tục.", "warning");';
const newToast = 'showToast(uiText("portal.form.requiredWarning", "Hãy hoàn tất các trường bắt buộc trước khi tiếp tục."), "warning");';
const additions = '  MESSAGES.vi["portal.form.requiredWarning"] = "Hãy hoàn tất các trường bắt buộc trước khi tiếp tục.";\n' +
  '  MESSAGES.en["portal.form.requiredWarning"] = "Complete the required fields before continuing.";\n' +
  '  MESSAGES.zh["portal.form.requiredWarning"] = "请先填写必填项，然后继续。";\n\n';
const rows = [
  {file: "static/portal/portal.js", old: oldToast, replacement: newToast},
  {file: "static/portal/portal-i18n.js", old: "  verifyEqualKeysets();", replacement: additions + "  verifyEqualKeysets();"}
];

for (const row of rows) test(`${row.file}: exact reviewed forward change and strict historical comparison`, () => {
  const original = lf(execFileSync("git", ["show", base + ":" + row.file], {encoding: "utf8", maxBuffer: 20e6}));
  const actual = imageStudioFieldsHistoricalSource(lf(fs.readFileSync(row.file, "utf8")), row.file);
  assert.equal(original.split(row.old).length - 1, 1);
  assert.equal(actual, original.replace(row.old, () => row.replacement));
  assert.equal(inverse(actual, row.file), original);
  assert.equal(inverse(original, row.file), original);
  assert.equal(inverse("/* customer */\n" + actual, row.file), "/* customer */\n" + original);
  assert.equal(inverse(actual, "customer/unrelated.js"), actual);
  assert.throws(() => inverse(actual + "\n" + row.replacement, row.file), /Unreviewed required-field warning/);
  const altered = row.file.endsWith("portal.js")
    ? actual.replace(newToast, newToast.replace("uiText(", "uiTextUnknown("))
    : actual.replace("Complete the required fields before continuing.", "UNREVIEWED");
  assert.throws(() => inverse(altered, row.file), /Unreviewed required-field warning/);
});

for (const [locale, value] of Object.entries({
  vi: "Hãy hoàn tất các trường bắt buộc trước khi tiếp tục.",
  en: "Complete the required fields before continuing.",
  zh: "请先填写必填项，然后继续。"
})) test(`${locale}: historical snapshot removes only the reviewed warning`, () => {
  const outside = ["customer", "unchanged"];
  const entries = [outside, ["portal.form.requiredWarning", value]];
  assert.deepEqual(snapshot(entries, locale), [outside]);
  assert.equal(snapshot(entries, locale)[0], outside);
  assert.throws(() => snapshot([...entries, entries[1]], locale), /Unreviewed required-field warning/);
  assert.throws(() => snapshot([outside, [entries[1][0], "UNREVIEWED"]], locale), /Unreviewed required-field warning/);
});
