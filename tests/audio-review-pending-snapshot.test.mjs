import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {audioReviewPendingHistoricalSource as project, audioReviewPendingHistoricalSnapshot as snapshot}
  from "./helpers/audio-review-pending-snapshot.mjs";

const fixture = JSON.parse(fs.readFileSync(new URL("./fixtures/audio-review-pending-contract.json", import.meta.url), "utf8"));
const files = ["static/portal/integration.js", "static/portal/portal-i18n.js"];
const base = Object.fromEntries(files.map(file => [file,
  execFileSync("git", ["show", fixture.base + ":" + file], {encoding: "utf8", maxBuffer: 20e6}).replace(/\r\n/g, "\n")]));
const candidate = {...base};
for (const row of fixture.records) {
  assert.equal(candidate[row.file].split(row.old).length - 1, 1);
  candidate[row.file] = candidate[row.file].replace(row.old, () => row.new);
}

for (const file of files) test(`${file}: historical projection restores exact base and keeps outside bytes`, () => {
  assert.equal(project(candidate[file], file), base[file]);
  assert.equal(project(base[file], file), base[file]);
  assert.equal(project("/* customer */\n" + candidate[file] + "\n/* tail */", file), "/* customer */\n" + base[file] + "\n/* tail */");
  assert.equal(project(candidate[file], "customer/unrelated.js"), candidate[file]);
  assert.equal(project(candidate[file], "toString"), candidate[file]);
});

for (const [index, row] of fixture.records.entries()) test(`record ${index + 1}: altered and duplicated changes are rejected`, () => {
  const current = candidate[row.file];
  const changed = index === 0 ? row.new.replace("throw error;", "throw new Error('altered');")
    : row.new.replace("review.", "unreviewed.");
  assert.notEqual(changed, row.new);
  assert.throws(() => project(current.replace(row.new, () => changed), row.file), /Unreviewed audio review pending feedback/);
  assert.throws(() => project(current + "\n" + row.new, row.file), /Unreviewed audio review pending feedback/);
  if (row.file.endsWith("integration.js"))
    assert.throws(() => project(current.replace(row.new, () => row.old), row.file), /Unreviewed audio review pending feedback/);
});

function messages(source) {
  const box = {window: {}};
  vm.runInNewContext(source, box);
  return box.window.TOANAASI18n.messages;
}
const actual = messages(candidate[files[1]]), original = messages(base[files[1]]);
for (const locale of ["vi", "en", "zh"]) test(`${locale}: historical catalogue strips only three verified entries`, () => {
  const entries = Object.entries(actual[locale]), expected = Object.entries(original[locale]);
  assert.deepEqual(snapshot(entries, locale), expected);
  const keys = ["audioWorkspace.feedback.review.notFound", "audioWorkspace.feedback.review.conflict", "audioWorkspace.feedback.review.maintenance"];
  assert.throws(() => snapshot(entries.filter(([key]) => key !== keys[0]), locale), /Unreviewed audio review pending feedback/);
  assert.throws(() => snapshot([...entries, entries.find(([key]) => key === keys[0])], locale), /Unreviewed audio review pending feedback/);
  assert.throws(() => snapshot(entries.map(row => row[0] === keys[1] ? [row[0], "UNKNOWN"] : row), locale), /Unreviewed audio review pending feedback/);
  const outside = entries.find(([key]) => !keys.includes(key));
  assert.equal(snapshot(entries, locale).find(([key]) => key === outside[0]), outside);
  assert.equal(snapshot(expected, locale), expected);
});
