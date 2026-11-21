import assert from "node:assert/strict";
import test from "node:test";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {ROOT, hash} from "./helpers/media-fixed-feedback-runtime.mjs";
import {mediaFixedFeedbackHistoricalSource as project, mediaFixedFeedbackHistoricalSnapshot as snapshot}
  from "./helpers/media-fixed-feedback-snapshot.mjs";
import {audioReviewHistoricalSource} from "./helpers/audio-review-snapshot.mjs";

const f = JSON.parse(fs.readFileSync(path.join(ROOT, "tests/fixtures/media-fixed-feedback-reviewed.json"), "utf8"));
const contract = JSON.parse(fs.readFileSync(path.join(ROOT, f.rootContractFile), "utf8"));
const lf = source => source.replace(/\r\n/g, "\n");
const current = Object.fromEntries(f.allowedFiles.map(file => [file,
  audioReviewHistoricalSource(lf(fs.readFileSync(path.join(ROOT, file), "utf8")), file)]));
const original = Object.fromEntries(f.allowedFiles.map(file => [file, lf(execFileSync("git", ["show", f.base + ":" + file],
  {cwd: ROOT, encoding: "utf8", maxBuffer: 30e6, windowsHide: true}))]));
function catalogue(source) {
  const box = {window: {}}; vm.runInNewContext(source, box, {timeout: 10000});
  return box.window.TOANAASI18n.messages;
}
const liveMessages = catalogue(current["static/portal/portal-i18n.js"]);
const baseMessages = catalogue(original["static/portal/portal-i18n.js"]);
test("finite newest source leaf restores complete BASE, is idempotent and preserves every outside byte", () => {
  const prefix = "/* CUSTOMER Facebook TikTok outside */\n", suffix = "\n/* CUSTOMER outside tail */";
  for (const file of f.allowedFiles) {
    assert.equal(project(current[file], file), original[file]);
    assert.equal(project(original[file], file), original[file]);
    assert.equal(project(project(current[file], file), file), original[file]);
    assert.equal(project(prefix + current[file] + suffix, file), prefix + original[file] + suffix);
    assert.equal(project(current[file], "customer/unrelated.txt"), current[file]);
  }
});
for (const [index, fragment] of f.historicalFragments.entries()) {
  test(`finite owned region${index + 1} rejects changed, duplicate, partial or moved current bytes`, () => {
    const source = current[fragment.file], altered = fragment.new.replace(/mediaWorkspaceFeedbackText|mediaWorkspaceErrorText|audioWorkspace\.feedback/, "UNREVIEWED_OWNED");
    assert.notEqual(altered, fragment.new);
    assert.throws(() => project(source.replace(fragment.new, () => altered), fragment.file), /Unreviewed media fixed feedback/);
    assert.throws(() => project(source + "\n" + fragment.new, fragment.file), /Unreviewed media fixed feedback/);
    assert.throws(() => project(source.replace(fragment.new, "") + "\n" + fragment.new, fragment.file), /Unreviewed media fixed feedback/);
    if (fragment.file.endsWith("integration.js")) {
      assert.throws(() => project(source.replace(fragment.new, fragment.old), fragment.file), /Unreviewed media fixed feedback/);
    }
  });
}
for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}: newest43 rows restore full BASE catalogue and retain unrelated entry references`, () => {
    const entries = Object.entries(liveMessages[locale]), before = JSON.stringify(entries);
    const expected = Object.entries(baseMessages[locale]);
    assert.deepEqual(snapshot(entries, locale), expected);
    const sentinel = ["customer.literal", "Facebook TikTok <img>"];
    const projected = snapshot([sentinel, ...entries, ["customer.tail", "media"]], locale);
    assert.equal(projected[0], sentinel);
    assert.deepEqual(projected.slice(1, -1), expected);
    assert.equal(JSON.stringify(entries), before);
    assert.equal(snapshot(expected, locale), expected, "Old inputs keep object identity");
  });
  test(`${locale}: unknown, partial, reordered, duplicate or changed owned catalogue rows cannot be hidden`, () => {
    const entries = Object.entries(liveMessages[locale]), rows = [...contract.errors, ...contract.toasts];
    const first = "audioWorkspace.feedback." + rows[0].key, second = "audioWorkspace.feedback." + rows[1].key;
    assert.throws(() => snapshot(entries.filter(([key]) => key !== first), locale), /Unreviewed media fixed feedback/);
    assert.throws(() => snapshot([...entries, [first, rows[0][locale]]], locale), /Unreviewed media fixed feedback/);
    assert.throws(() => snapshot(entries.map(row => row[0] === first ? [first, "UNKNOWN"] : row), locale), /Unreviewed media fixed feedback/);
    const swapped = entries.map(row => row[0] === first ? [second, rows[1][locale]] : row[0] === second ? [first, rows[0][locale]] : row);
    assert.throws(() => snapshot(swapped, locale), /Unreviewed media fixed feedback/);
    assert.throws(() => snapshot([...entries, ["audioWorkspace.feedback.unknown", "UNKNOWN"]], locale), /Unreviewed media fixed feedback/);
  });
}
test("reviewed provenance retains three exact worker groups and complete151 forward pins without changing the Root expected contract", () => {
  assert.equal(f.canonicalRecords, 11); assert.deepEqual(f.workers.map(row => row.records), [2, 8, 1]);
  assert.ok(f.workers.every(row => row.codeFailures === 0 && row.fullMapExact && row.publicSourcesExact === 3));
  assert.equal(f.openCritical, 0); assert.equal(f.openImportant, 0);
  assert.equal(hash(fs.readFileSync(path.join(ROOT, f.rootContractFile))), f.rootContractRawSha256);
  for (const row of f.applicationBaseline) {
    assert.equal(hash(audioReviewHistoricalSource(lf(fs.readFileSync(path.join(ROOT, row.file), "utf8")), row.file)),
      row.candidateLfSha256, row.file);
  }
});
