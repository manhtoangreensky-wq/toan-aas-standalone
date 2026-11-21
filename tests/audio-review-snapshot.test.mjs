import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import {execFileSync} from "node:child_process";
import {ROOT, hash} from "./helpers/audio-review-feedback-runtime.mjs";
import {audioReviewHistoricalSource as project, audioReviewHistoricalSnapshot as snapshot}
  from "./helpers/audio-review-snapshot.mjs";
import {mediaFixedFeedbackHistoricalSource as olderProject}
  from "./helpers/media-fixed-feedback-snapshot.mjs";
import {audioReviewVisualHistoricalSource} from "./helpers/audio-review-visual-snapshot.mjs";
import {audioReviewPendingHistoricalSource} from "./helpers/audio-review-pending-snapshot.mjs";

const fixture = JSON.parse(fs.readFileSync(path.join(ROOT, "tests/fixtures/audio-review-reviewed.json"), "utf8"));
const contract = JSON.parse(fs.readFileSync(path.join(ROOT, fixture.rootContractFile), "utf8"));
const lf = value => value.replace(/\r\n/g, "\n");
const current = Object.fromEntries(fixture.allowedFiles.map(file => [file,
  audioReviewVisualHistoricalSource(audioReviewPendingHistoricalSource(lf(fs.readFileSync(path.join(ROOT, file), "utf8")), file), file)]));
const base = Object.fromEntries(fixture.allowedFiles.map(file => [file, lf(execFileSync("git", ["show", fixture.base + ":" + file],
  {cwd: ROOT, encoding: "utf8", maxBuffer: 30e6, windowsHide: true}))]));
const fail = /Unreviewed audio review/;
function catalogue(source) {
  const box = {window: {}}; vm.runInNewContext(source, box, {timeout: 10000});
  return box.window.TOANAASI18n.messages;
}
const live = catalogue(current["static/portal/portal-i18n.js"]), original = catalogue(base["static/portal/portal-i18n.js"]);
test("ARF finite historical leaf restores all3 complete BASE sources, is idempotent and preserves every outside byte", () => {
  const before = "/* CUSTOMER literal outside prefix */\n", after = "\n/* CUSTOMER literal outside tail */";
  for (const file of fixture.allowedFiles) {
    assert.equal(project(current[file], file), base[file]);
    assert.equal(project(base[file], file), base[file]);
    assert.equal(project(project(current[file], file), file), base[file]);
    assert.equal(project(before + current[file] + after, file), before + base[file] + after);
    assert.equal(project(current[file], "customer/unrelated.js"), current[file]);
  }
});
for (const [index, region] of fixture.historicalFragments.entries()) {
  test(`ARF bounded region${index + 1} rejects changed, duplicate, partial, moved and owner/next corruption`, () => {
    const source = current[region.file];
    const changed = region.new.replace("review", "unreviewed");
    assert.notEqual(changed, region.new);
    assert.throws(() => project(source.replace(region.new, () => changed), region.file), fail);
    assert.throws(() => project(source + "\n" + region.new, region.file), fail);
    assert.throws(() => project(source.replace(region.new, "") + "\n" + region.new, region.file), fail);
    const partial = region.new.slice(0, Math.floor(region.new.length / 2));
    assert.throws(() => project(source.replace(region.new, () => partial), region.file), fail);
    assert.throws(() => project(source.replace(region.owner, () => region.owner + " UNREVIEWED"), region.file), fail);
    assert.throws(() => project(source.replace(region.next, () => region.next.replace(/\S/, "X")), region.file), fail);
    if (region.file.endsWith("integration.js")) {
      assert.throws(() => project(source.replace(region.new, () => region.old), region.file), fail);
    }
  });
}
test("ARF renderer-only patch cannot be disguised as an old input by deleting its display helper", () => {
  const file = "static/portal/portal.js", region = fixture.historicalFragments.find(row => row.file === file);
  const helperOnly = region.new.slice(0, region.new.indexOf(region.oldOwner));
  const rendererOnly = current[file].replace(helperOnly, "");
  assert.ok(rendererOnly.includes(contract.renderer.new));
  assert.throws(() => project(rendererOnly, file), fail);
  assert.throws(() => project(rendererOnly.replaceAll("audioHubReviewSourceText", "UNKNOWN_DISPLAY"), file), fail);
});
test("ARF catalogue append cannot move outside verification and freeze ownership fences", () => {
  const file = "static/portal/portal-i18n.js", region = fixture.historicalFragments.find(row => row.file === file);
  const without = current[file].replace(region.new, "");
  const verify = "  function verifyEqualKeysets() {";
  assert.throws(() => project(without.replace(verify, region.new + "\n" + verify), file), fail);
  assert.throws(() => project(without + "\n" + region.new, file), fail);
});
test("ARF projection preserves unrelated MFF mutations so the older comparator keeps its own error identity", () => {
  const file = "static/portal/integration.js";
  const source = current[file].replace("  function mediaWorkspaceFeedbackText(key, fallback) {",
    "  function mediaWorkspaceFeedbackText(key, fallback) { /* MFF malformed outside ARF */");
  const stripped = project(source, file);
  assert.ok(stripped.includes("/* MFF malformed outside ARF */"));
  assert.throws(() => olderProject(source, file), /Unreviewed media fixed feedback/);
});
test("historical MFF malformed overlapping catch input is tested only after reviewed ARF strip", () => {
  const file = "static/portal/integration.js", stripped = project(current[file], file);
  const malformed = stripped.replace("      const editorialError = ", "      const editorialError = /* MFF malformed */");
  assert.equal(project(malformed, file), malformed, "No current ARF marker means no interception");
  assert.throws(() => olderProject(malformed, file), /Unreviewed media fixed feedback/);
});
for (const locale of ["vi", "en", "zh"]) {
  test(`${locale}/ARF31 rows restore exact complete BASE catalogue and deep input identity`, () => {
    const entries = Object.entries(live[locale]), expected = Object.entries(original[locale]);
    const before = JSON.stringify(entries), projected = snapshot(entries, locale);
    assert.deepEqual(projected, expected); assert.equal(JSON.stringify(entries), before);
    assert.equal(snapshot(expected, locale), expected, "Historical catalogue retains array identity");
    const unrelated = entries.find(([key]) => !contract.copyRows.some(row => row.key === key));
    assert.ok(unrelated); assert.equal(projected.find(([key]) => key === unrelated[0]), unrelated);
    const prefix = ["customer.prefix", "CUSTOMER <img>"], suffix = ["customer.tail", "CUSTOMER & audio"];
    const decorated = snapshot([prefix, ...entries, suffix], locale);
    assert.equal(decorated[0], prefix); assert.equal(decorated.at(-1), suffix);
    assert.deepEqual(decorated.slice(1, -1), expected);
  });
  test(`${locale}/ARF partial, unknown, reorder, changed, duplicate or incorrect override cannot be hidden`, () => {
    const entries = Object.entries(live[locale]), added = [...contract.feedback, ...contract.resultRows];
    const [first, second] = added, override = contract.staticRows[0];
    assert.throws(() => snapshot(entries.filter(([key]) => key !== first.key), locale), fail);
    assert.throws(() => snapshot([...entries, [first.key, first[locale]]], locale), fail);
    assert.throws(() => snapshot([...entries, ["audioWorkspace.feedback.review.unknown", "UNKNOWN"]], locale), fail);
    assert.throws(() => snapshot([...entries, ["audioWorkspace.review.result.unknown", "UNKNOWN"]], locale), fail);
    assert.throws(() => snapshot(entries.map(entry => entry[0] === first.key ? [first.key, "UNKNOWN"] : entry), locale), fail);
    assert.throws(() => snapshot(entries.map(entry => entry[0] === first.key ? [second.key, second[locale]]
      : entry[0] === second.key ? [first.key, first[locale]] : entry), locale), fail);
    const gap = entries.findIndex(([key]) => key === second.key);
    assert.throws(() => snapshot([...entries.slice(0, gap), ["customer.gap", "literal"], ...entries.slice(gap)], locale), fail);
    assert.throws(() => snapshot(entries.map(entry => entry[0] === override.key ? [override.key, "UNKNOWN"] : entry), locale), fail);
    assert.throws(() => snapshot([...entries, [override.key, override[locale]]], locale), fail);
    assert.throws(() => snapshot(entries.filter(([key]) => key !== override.key), locale), fail);
    assert.throws(() => snapshot(entries.filter(([key]) => !added.some(row => row.key === key)), locale), fail);
    const oldEntries = Object.entries(original[locale]);
    assert.throws(() => snapshot(oldEntries.map(entry => entry[0] === override.key
      ? [override.key, override[locale]] : entry), locale), fail);
  });
}
test("ARF source composition restores portal before the MFF file allowlist return", () => {
  const file = "static/portal/portal.js";
  assert.equal(olderProject(current[file], file), base[file]);
});
test("ARF reviewed provenance pins11 records,5 regions,31 copy rows,3 groups and151 candidate sources", () => {
  assert.equal(fixture.canonicalRecords, 11); assert.equal(fixture.historicalFragments.length, 5);
  assert.equal(fixture.copyRows.length, 31); assert.deepEqual(fixture.copyRows, contract.copyRows);
  assert.deepEqual(fixture.workers.map(row => row.records), [8, 2, 1]);
  assert.ok(fixture.workers.every(row => row.codeFailures === 0 && row.fullMapExact && row.publicSourcesExact === 4));
  assert.equal(fixture.workerCodeFailures, 0); assert.equal(fixture.applicationTakeover, false);
  assert.equal(fixture.source151ForwardExact, true); assert.equal(fixture.protected148Exact, true);
  assert.equal(fixture.protectedFunctionsExact, 21);
  assert.equal(hash(fs.readFileSync(path.join(ROOT, fixture.rootContractFile))), fixture.rootContractRawSha256);
  assert.equal(fixture.applicationBaseline.length, 151);
  for (const row of fixture.applicationBaseline) {
    assert.equal(hash(audioReviewVisualHistoricalSource(audioReviewPendingHistoricalSource(lf(fs.readFileSync(path.join(ROOT, row.file), "utf8")), row.file), row.file)), row.candidateLfSha256, row.file);
  }
});
